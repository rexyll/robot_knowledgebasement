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
    assert "colcon build" in content
    assert "--install-base" in content
    assert "install_manifest.txt" in content
    assert "--export-root" in content


def test_build_matrix_requires_pinned_clean_jazzy_source():
    content = SCRIPT.read_text(encoding="utf-8")
    assert "bd658e2d266e315d2ee35f985fb352ea88306b79" in content
    assert '[[ -z "$(git -C "${SOURCE_DIR}" status --porcelain)" ]]' in content
    assert '[[ "${ROS_DISTRO}" == "jazzy" ]]' in content


def test_build_matrix_runs_install_space_consumer_in_both_modes():
    content = SCRIPT.read_text(encoding="utf-8")
    assert content.count("INSTALL_SPACE_CONSUMER_PASS BUILD_TESTING=%s") == 1
    assert "for mode in OFF ON; do" in content
    assert "find_package(staubli_robot_driver REQUIRED)" in content
    assert "colcon test-result" in content
    assert "unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH" in content
    assert "unset PYTHONPATH LD_LIBRARY_PATH ROS_PACKAGE_PATH" in content
    assert 'source "${install_base}/setup.bash"' in content
    assert "Run each consumer in a clean ROS environment" in content


def test_build_matrix_shell_syntax_is_valid():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


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
