import json
from argparse import Namespace

from scripts.validate_staubli_upstream_target_graph import (
    DIAGNOSTIC_TARGET,
    GTEST_TARGETS,
    PRODUCTION_TARGETS,
    validate,
)


def snapshot(configuration_id, build_testing, targets, install_entries, exported_targets):
    return {
        "configuration_id": configuration_id,
        "build_testing": build_testing,
        "targets": targets,
        "install_entries": install_entries,
        "exported_targets": exported_targets,
    }


def args(off, on):
    return Namespace(build_off=off, build_on=on, report=None)


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def valid_pair(tmp_path):
    production = [
        {"name": PRODUCTION_TARGETS[0], "type": "SHARED_LIBRARY", "dependencies": []},
        {
            "name": PRODUCTION_TARGETS[1],
            "type": "SHARED_LIBRARY",
            "dependencies": [PRODUCTION_TARGETS[0]],
        },
        {"name": DIAGNOSTIC_TARGET, "type": "EXECUTABLE", "dependencies": [PRODUCTION_TARGETS[0]]},
    ]
    tests = [
        {"name": name, "type": "EXECUTABLE", "dependencies": [PRODUCTION_TARGETS[0]]}
        for name in GTEST_TARGETS
    ]
    installs = [
        "lib/libstaubli_robot_driver.so",
        "lib/libstaubli_robot_driver_hardware_interface.so",
        "lib/staubli_robot_driver/test_receive_robot_state",
    ]
    exports = [
        "staubli_robot_driver::staubli_robot_driver",
        "staubli_robot_driver::staubli_robot_driver_hardware_interface",
    ]
    off = snapshot("off", False, production, installs, exports)
    on = snapshot("on", True, production + tests, installs, exports)
    return (
        write(tmp_path, "off.json", off),
        write(tmp_path, "on.json", on),
    )


def test_fixed_upstream_target_matrix_passes(tmp_path):
    off, on = valid_pair(tmp_path)
    report = validate(args(off, on))
    assert report["execution_status"] == "PASS"
    assert report["error_count"] == 0


def test_gtest_targets_must_be_absent_when_testing_off(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(off.read_text())
    data["targets"].append({"name": GTEST_TARGETS[0], "dependencies": []})
    off.write_text(json.dumps(data), encoding="utf-8")
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert any("GTEST-ABSENT-OFF-" in error for error in report["errors"])


def test_gtest_targets_must_exist_when_testing_on(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(on.read_text())
    data["targets"] = [
        item for item in data["targets"] if item["name"] != GTEST_TARGETS[0]
    ]
    on.write_text(json.dumps(data), encoding="utf-8")
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert any("GTEST-PRESENT-ON-" in error for error in report["errors"])


def test_production_dependency_on_gtest_fails(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(on.read_text())
    data["targets"][1]["dependencies"].append(GTEST_TARGETS[0])
    on.write_text(json.dumps(data), encoding="utf-8")
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert any("PRODUCTION-CLOSURE-EXCLUDES-TESTS" in error for error in report["errors"])


def test_gtest_install_or_export_leak_fails(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(on.read_text())
    data["install_entries"].append(f"lib/{GTEST_TARGETS[0]}")
    data["exported_targets"].append(GTEST_TARGETS[0])
    on.write_text(json.dumps(data), encoding="utf-8")
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert any("INSTALL-EXCLUDES-GTEST-ON" in error for error in report["errors"])
    assert any("EXPORT-EXCLUDES-GTEST-ON" in error for error in report["errors"])


def test_diagnostic_utility_must_remain_installed(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(off.read_text())
    data["install_entries"] = [
        item for item in data["install_entries"] if DIAGNOSTIC_TARGET not in item
    ]
    off.write_text(json.dumps(data), encoding="utf-8")
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert any("DIAGNOSTIC-INSTALLED-OFF" in error for error in report["errors"])


def test_export_set_must_contain_both_production_libraries(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(on.read_text())
    data["exported_targets"] = data["exported_targets"][:1]
    on.write_text(json.dumps(data), encoding="utf-8")
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert any("EXPORT-PRODUCTION-TARGETS-ON" in error for error in report["errors"])


def test_snapshot_testing_flags_must_match_configuration(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(off.read_text())
    data["build_testing"] = True
    off.write_text(json.dumps(data), encoding="utf-8")
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert any("CONFIG-BUILD-TESTING-OFF" in error for error in report["errors"])
