from __future__ import annotations

import ast
from pathlib import Path

import pytest

from software.readonly_capture import capture_snapshot, load_register_whitelist


class FakeBus:
    def __init__(self, fail_on: tuple[str, str] | None = None):
        self.calls: list[tuple[str, str, bool, int]] = []
        self.fail_on = fail_on

    def read(self, data_name, motor, *, normalize=False, num_retry=0):
        self.calls.append((data_name, motor, normalize, num_retry))
        if self.fail_on == (data_name, motor):
            raise TimeoutError("simulated timeout")
        return 123


def test_whitelist_is_nonempty_and_unique():
    whitelist = load_register_whitelist()
    names = [item["name"] for item in whitelist["registers"]]
    assert names
    assert len(names) == len(set(names))
    assert whitelist["read_operation_only"] is True


def test_collector_uses_only_read_and_disables_normalization_and_retries():
    bus = FakeBus()
    result = capture_snapshot(bus, {"shoulder_pan": 1, "shoulder_lift": 2})
    fields = load_register_whitelist()["registers"]
    assert len(bus.calls) == 2 * len(fields)
    assert all(normalize is False and retries == 0 for _, _, normalize, retries in bus.calls)
    assert all(motor in {"shoulder_pan", "shoulder_lift"} for _, motor, _, _ in bus.calls)
    assert all(record["result"] == "ok" for record in result["records"])
    assert all(record["register_value_decoded"] == 123 for record in result["records"])
    assert all("wire_bytes" not in record for record in result["records"])


def test_failed_field_is_recorded_without_zero_filling():
    bus = FakeBus(fail_on=("present_voltage", "shoulder_pan"))
    result = capture_snapshot(bus, {"shoulder_pan": 1})
    failed = [
        record for record in result["records"]
        if record["field"] == "present_voltage"
    ]
    assert len(failed) == 1
    assert failed[0]["result"] == "error"
    assert failed[0]["exception_type"] == "TimeoutError"
    assert "register_value_decoded" not in failed[0]


def test_empty_motor_map_is_rejected():
    with pytest.raises(ValueError):
        capture_snapshot(FakeBus(), {})


def test_collector_source_has_no_write_or_private_bus_calls():
    source_path = Path(__file__).parents[1] / "readonly_capture.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden = {
        "write", "sync_write", "setup_motor", "set_baudrate", "configure_motors",
        "set_operating_mode", "enable_torque", "disable_torque", "set_torque",
        "read_calibration", "write_calibration", "disconnect", "_bus", "_connected_bus",
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert called_attributes.isdisjoint(forbidden)
