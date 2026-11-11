import json
from argparse import Namespace

from scripts.validate_staubli_fake_harness_target_graph import validate


def snapshot(configuration_id, targets, install_entries=None, exported_targets=None):
    return {
        "configuration_id": configuration_id,
        "targets": targets,
        "install_entries": install_entries or [],
        "exported_targets": exported_targets or [],
    }


def args(off, on):
    return Namespace(
        build_off=off,
        build_on=on,
        report=None,
        production_target=["staubli_socket_core", "staubli_driver_plugin"],
        test_target=["staubli_socket_test_support", "staubli_socket_unit_tests"],
        plugin_target="staubli_driver_plugin",
    )


def write(tmp_path, name, value):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def valid_pair(tmp_path):
    off = snapshot("off", [
        {"name": "staubli_socket_core", "dependencies": []},
        {"name": "staubli_driver_plugin", "dependencies": ["staubli_socket_core"]},
    ])
    on = snapshot("on", [
        {"name": "staubli_socket_core", "dependencies": []},
        {"name": "staubli_driver_plugin", "dependencies": ["staubli_socket_core"]},
        {"name": "staubli_socket_test_support", "dependencies": ["staubli_socket_core"]},
        {"name": "staubli_socket_unit_tests", "dependencies": ["staubli_socket_test_support"]},
    ], ["lib/libstaubli_socket_core.so", "lib/libstaubli_driver_plugin.so"],
       ["staubli_socket_core", "staubli_driver_plugin"])
    return write(tmp_path, "off.json", off), write(tmp_path, "on.json", on)


def test_valid_build_matrix_and_isolation_pass(tmp_path):
    off, on = valid_pair(tmp_path)
    report = validate(args(off, on))
    assert report["execution_status"] == "PASS"
    assert report["error_count"] == 0


def test_test_target_must_not_exist_when_testing_off(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(off.read_text())
    data["targets"].append({"name": "staubli_socket_test_support", "dependencies": []})
    off.write_text(json.dumps(data))
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert any("TEST-OFF-" in error for error in report["errors"])


def test_production_transitive_dependency_on_fake_fails(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(on.read_text())
    data["targets"][1]["dependencies"].append("staubli_socket_test_support")
    on.write_text(json.dumps(data))
    report = validate(args(off, on))
    assert "PROD-CLOSURE-ZERO-FAKE" in [item["id"] for item in report["checks"] if item["status"] == "FAIL"]
    assert report["execution_status"] == "FAIL"


def test_install_or_export_leak_fails(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(on.read_text())
    data["install_entries"].append("include/testing/FakeClock.hpp")
    data["exported_targets"].append("staubli_socket_test_support")
    on.write_text(json.dumps(data))
    report = validate(args(off, on))
    assert report["execution_status"] == "FAIL"
    assert "INSTALL-ZERO-FAKE" in [x["id"] for x in report["checks"] if x["status"] == "FAIL"]
    assert "EXPORT-ZERO-FAKE" in [x["id"] for x in report["checks"] if x["status"] == "FAIL"]


def test_plugin_transitive_fake_dependency_fails(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(on.read_text())
    data["targets"][1]["dependencies"].append("staubli_socket_test_support")
    on.write_text(json.dumps(data))
    report = validate(args(off, on))
    assert "PLUGIN-ZERO-FAKE" in [x["id"] for x in report["checks"] if x["status"] == "FAIL"]


def test_duplicate_target_is_rejected(tmp_path):
    off, on = valid_pair(tmp_path)
    data = json.loads(on.read_text())
    data["targets"].append({"name": "staubli_socket_core", "dependencies": []})
    on.write_text(json.dumps(data))
    try:
        validate(args(off, on))
    except ValueError as exc:
        assert "duplicate target" in str(exc)
    else:
        raise AssertionError("duplicate target must be rejected")
