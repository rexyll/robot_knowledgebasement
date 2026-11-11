import importlib.util
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "run_staubli_build_testing_matrix.sh"


def test_evidence_packager_uses_servo_906_report_name():
    packager = (
        Path(__file__).parents[1]
        / "scripts"
        / "package_staubli_build_evidence.py"
    ).read_text(encoding="utf-8")
    assert 'artifact_dir / "servo-906-validation-report.json"' in packager
    assert 'artifact_dir / "servo-901-validation-report.json"' not in packager


def test_build_matrix_uses_fixed_upstream_validator_and_real_build_install():
    content = SCRIPT.read_text(encoding="utf-8")
    assert "validate_staubli_upstream_target_graph.py" in content
    assert "validate_staubli_fake_harness_target_graph.py" not in content
    assert "colcon --log-base" in content and " build \\" in content
    assert "--install-base" in content
    assert "install_manifest.txt" in content
    assert "--export-root" in content


def test_build_matrix_requires_pinned_clean_jazzy_source():
    content = SCRIPT.read_text(encoding="utf-8")
    assert "bd658e2d266e315d2ee35f985fb352ea88306b79" in content
    assert '[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain)" ]]' in content
    assert '[[ "${ROS_DISTRO}" == "jazzy" ]]' in content
    assert "find_package(backward_ros REQUIRED)" in content
    assert "cmake -S \"${dependency_probe_dir}\" -B \"${dependency_probe_dir}/build\"" in content
    assert "ros2 pkg prefix backward_ros" not in content


def test_build_matrix_runs_install_space_consumer_in_both_modes():
    content = SCRIPT.read_text(encoding="utf-8")
    assert content.count("INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=%s") == 1
    assert "for mode in OFF ON; do" in content
    assert "find_package(staubli_robot_driver REQUIRED)" in content
    assert "colcon test-result" in content
    assert "unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH" in content
    assert "unset PYTHONPATH LD_LIBRARY_PATH ROS_PACKAGE_PATH" in content
    assert 'source_ros_environment "${install_base}/setup.bash"' in content
    assert "Run each consumer in a clean ROS environment" in content


def test_build_matrix_requires_all_upstream_gtest_xml_reports_to_pass():
    content = SCRIPT.read_text(encoding="utf-8")
    expected = {
        "test_primitives_serialization.gtest.xml",
        "test_message_serialization.gtest.xml",
        "test_sockets.gtest.xml",
        "test_rt_socket_interface.gtest.xml",
        "test_robot_driver.gtest.xml",
        "test_mock_robot_server.gtest.xml",
        "test_staubli_hardware_interface.gtest.xml",
    }
    for report in expected:
        assert report in content
    assert "gtest result inventory mismatch" in content
    assert "UPSTREAM_GTEST_XML_PASS" in content
    assert 'int(root.attrib.get("tests", "0"))' in content
    assert 'int(root.attrib.get("failures", "0"))' in content
    assert 'int(root.attrib.get("errors", "0"))' in content


def test_build_matrix_shell_syntax_is_valid():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr



def test_colcon_global_log_base_precedes_each_verb():
    content = SCRIPT.read_text(encoding="utf-8")
    assert 'run_logged colcon --log-base "${log_base}" build' in content
    assert 'run_logged colcon --log-base "${CONSUMER_ROOT}/logs-${lower}" build' in content
    assert 'run_logged colcon --log-base "${LOG_ROOT}/colcon-on" test' in content
    assert 'colcon build \\\n    --base-paths' not in content
    assert 'colcon test \\\n  --base-paths' not in content

def test_manual_ros_workflow_refreshes_apt_indexes_before_rosdep_install():
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "staubli-ros-jazzy-build.yml"
    ).read_text(encoding="utf-8")
    dependency_step = workflow.split("      - name: Resolve declared ROS dependencies", 1)[1]
    assert dependency_step.index("rosdep update") < dependency_step.index("apt-get update")
    assert dependency_step.index("apt-get update") < dependency_step.index("rosdep install")
    assert "rm -rf /var/lib/apt/lists/*" not in workflow


def test_manual_ros_workflow_pins_image_and_upstream_source():
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "staubli-ros-jazzy-build.yml"
    ).read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    image_digest = (
        "osrf/ros@sha256:"
        "ae7ad3ac243da1dfd8bd402a2fa08e149ffbf7a385013bd8ef798d0800accdc8"
    )
    assert image_digest in workflow
    assert "bd658e2d266e315d2ee35f985fb352ea88306b79" in workflow
    assert "ros-jazzy-backward-ros" in workflow
    assert "bash scripts/run_staubli_build_testing_matrix.sh" in workflow
    assert "staubli-ros-jazzy-build-install-evidence" in workflow


def test_install_consumer_links_exported_target_directly():
    content = SCRIPT.read_text(encoding="utf-8")
    assert (
        "target_link_libraries(staubli_install_consumer PRIVATE "
        "staubli_robot_driver::staubli_robot_driver)"
    ) in content
    assert (
        "ament_target_dependencies(staubli_install_consumer staubli_robot_driver)"
    ) not in content


def test_install_consumer_calls_an_out_of_line_library_symbol():
    content = SCRIPT.read_text(encoding="utf-8")
    assert '#include "staubli_robot_driver/communication/protocol.hpp"' in content
    assert "header.serialize(buffer, sizeof(buffer))" in content
    assert "int main() { return 0; }" not in content


def test_install_consumer_compiles_public_realtime_tools_header():
    content = SCRIPT.read_text(encoding="utf-8")
    assert (
        '#include "staubli_robot_driver/real_time_socket_subscriber.hpp"'
    ) in content


def test_install_consumer_binary_is_executed_in_both_modes():
    content = SCRIPT.read_text(encoding="utf-8")
    consumer_command = (
        'run_logged "${CONSUMER_ROOT}/install-${lower}/lib/'
        "staubli_install_consumer/staubli_install_consumer"
    )
    assert consumer_command in content
    assert content.index(consumer_command) < content.index(
        "INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=%s"
    )


def test_build_matrix_does_not_require_unused_standalone_asio():
    content = SCRIPT.read_text(encoding="utf-8")
    workflow = (
        Path(__file__).parents[1]
        / ".github"
        / "workflows"
        / "staubli-ros-jazzy-build.yml"
    ).read_text(encoding="utf-8")
    assert "libboost-system-dev" in workflow
    assert "libasio-dev" not in workflow
    assert "libasio-dev" not in content
    assert "/usr/include/asio.hpp" not in content


def test_export_validator_checks_installed_include_directories():
    validator = (
        Path(__file__).parents[1]
        / "scripts"
        / "validate_staubli_upstream_target_graph.py"
    ).read_text(encoding="utf-8")
    collector = (
        Path(__file__).parents[1]
        / "scripts"
        / "collect_staubli_cmake_file_api.py"
    ).read_text(encoding="utf-8")
    assert "exported_target_include_directories" in collector
    assert "EXPORT-EXCLUDES-UNRESOLVED-ASIO-INCLUDE-" in validator
    assert 'value == "/asio/include"' in validator
    assert '"exported_target_include_directories" not in snapshot' in validator


def test_export_collector_captures_installed_include_directories():
    collector = (
        Path(__file__).parents[1]
        / "scripts"
        / "collect_staubli_cmake_file_api.py"
    ).read_text(encoding="utf-8")
    assert "exported_target_include_directories" in collector
    assert "INTERFACE_INCLUDE_DIRECTORIES" in collector
    assert "collect_exported_target_include_directories(prefix)" in collector


def test_export_collector_reads_installed_interface_include_directories(tmp_path):
    collector_path = (
        Path(__file__).parents[1]
        / "scripts"
        / "collect_staubli_cmake_file_api.py"
    )
    spec = importlib.util.spec_from_file_location(
        "staubli_cmake_file_api_collector", collector_path
    )
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)

    export_file = (
        tmp_path
        / "lib"
        / "cmake"
        / "staubli_robot_driver"
        / "staubli_robot_driverTargets.cmake"
    )
    export_file.parent.mkdir(parents=True)
    export_file.write_text(
        'set_target_properties(staubli_robot_driver::staubli_robot_driver '
        'PROPERTIES INTERFACE_INCLUDE_DIRECTORIES '
        '"${_IMPORT_PREFIX}/include;/asio/include")\n',
        encoding="utf-8",
    )

    assert collector.collect_exported_target_include_directories(tmp_path) == [
        "${_IMPORT_PREFIX}/include",
        "/asio/include",
    ]



def test_export_collector_finds_isolated_colcon_install_layout(tmp_path):
    collector_path = (
        Path(__file__).parents[1]
        / "scripts"
        / "collect_staubli_cmake_file_api.py"
    )
    spec = importlib.util.spec_from_file_location(
        "staubli_cmake_file_api_isolated_collector", collector_path
    )
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)

    export_file = (
        tmp_path
        / "staubli_robot_driver"
        / "share"
        / "staubli_robot_driver"
        / "cmake"
        / "staubli_robot_driverExport.cmake"
    )
    export_file.parent.mkdir(parents=True)
    export_file.write_text(
        'add_library(staubli_robot_driver::staubli_robot_driver SHARED IMPORTED)\n'
        'set_target_properties(staubli_robot_driver::staubli_robot_driver '
        'PROPERTIES INTERFACE_INCLUDE_DIRECTORIES '
        '"/isolated/include")\n',
        encoding="utf-8",
    )

    assert collector.find_export_files(tmp_path) == [export_file.resolve()]
    assert collector.collect_exported_target_include_directories(tmp_path) == [
        "/isolated/include"
    ]



def test_ros_setup_is_sourced_without_nounset_and_strict_mode_is_restored():
    content = SCRIPT.read_text(encoding="utf-8")
    assert "source_ros_environment()" in content
    assert "set +u" in content
    assert "set -u" in content
    assert 'source_ros_environment "${ROS_SETUP}"' in content
    assert 'source_ros_environment "${install_base}/setup.bash"' in content
    assert 'source "${ROS_SETUP}"' not in content


def test_install_consumer_does_not_mask_unexported_boost_dependency():
    content = SCRIPT.read_text(encoding="utf-8")
    marker = 'cat > "${consumer_src}/CMakeLists.txt" <<\'CMAKE\''
    consumer_cmake = content.split(marker, 1)[1].split("\nCMAKE", 1)[0]
    assert "find_package(staubli_robot_driver REQUIRED)" in consumer_cmake
    assert "find_package(Boost" not in consumer_cmake
    assert "Boost::system" not in consumer_cmake
    assert "CONSUMER_FAILURES_FILE" in content
    assert "INSTALL_SPACE_CONSUMER_FINDINGS_PRESENT" in content
    assert "installed CMake package consumer configure/build failed" in content
    assert "if run_logged colcon --log-base" in content
    assert 'run_logged colcon --log-base "${LOG_ROOT}/colcon-on" test' in content
