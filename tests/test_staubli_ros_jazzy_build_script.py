from pathlib import Path
import subprocess

SCRIPT = Path(__file__).parents[1] / "scripts" / "run_staubli_build_testing_matrix.sh"


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


def test_build_matrix_shell_syntax_is_valid():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
