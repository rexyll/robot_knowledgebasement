"""Explicit engineering-unit conversions for decoded FEETECH STS3215 readings.

Inputs are integers returned by the LeRobot/rustypot ServoDefinition read path:
wire bytes have already been decoded using the register's declared encoding.
This module does not parse wire bytes, connect to a bus, or modify servo state.

Only conversions with a documented generic STS scale are implemented here.
Position and speed are deliberately left unsupported pending an unambiguous
mode/encoding-specific conversion contract for the exact servo configuration.
"""
from __future__ import annotations

from typing import Any


_CONVERSIONS: dict[str, dict[str, Any]] = {
    "present_load": {
        "unit": "%",
        "scale": 0.1,
        "basis": "FEETECH generic STS tutorial: 0.1 percent per count; signed direction/magnitude.",
        "min_value": -1023,
        "max_value": 1023,
    },
    "present_voltage": {
        "unit": "V",
        "scale": 0.1,
        "basis": "FEETECH generic STS tutorial: 0.1 V per count.",
        "min_value": 0,
        "max_value": 255,
    },
    "present_temperature": {
        "unit": "degC",
        "scale": 1.0,
        "basis": "FEETECH generic STS tutorial: 1 degree Celsius per count.",
        "min_value": 0,
        "max_value": 255,
    },
    "present_current": {
        "unit": "A",
        "scale": 0.0065,
        "basis": "FEETECH generic STS tutorial: 6.5 mA per count; unsigned register.",
        "min_value": 0,
        "max_value": 65535,
    },
}

_SOURCE_URL = (
    "https://www.feetech.cn/Data/feetechrc/upload/file/20220618/"
    "%E5%85%88%E7%9C%8B%E8%BF%99%E9%87%8C-%E5%85%A5%E9%97%A8%E6%95%99%E7%A8%8B2-1.pdf"
)


def convert_decoded_reading(field: str, decoded_value: int) -> dict[str, Any]:
    """Convert one already-decoded STS3215 register integer to a documented unit.

    The decoded integer is always retained verbatim in the result. This helper
    intentionally rejects bool (a Python int subclass), floats, unknown fields,
    and values outside the register's representable range.
    """
    if not isinstance(decoded_value, int) or isinstance(decoded_value, bool):
        raise TypeError("decoded_value must be an integer returned by read_register")
    if field not in _CONVERSIONS:
        raise ValueError(
            f"No approved engineering-unit conversion for {field!r}; "
            "retain the decoded register integer"
        )

    spec = _CONVERSIONS[field]
    if not spec["min_value"] <= decoded_value <= spec["max_value"]:
        raise ValueError(
            f"{field} decoded value {decoded_value} is outside "
            f"[{spec['min_value']}, {spec['max_value']}]"
        )

    engineering_value = decoded_value * spec["scale"]
    if field == "present_temperature":
        engineering_value = int(engineering_value)

    return {
        "field": field,
        "register_value_decoded": decoded_value,
        "engineering_value": engineering_value,
        "engineering_unit": spec["unit"],
        "scale_to_unit": spec["scale"],
        "conversion_basis": spec["basis"],
        "source_url": _SOURCE_URL,
        "calibration_status": "not_calibrated",
        "scope_warning": (
            "Generic FEETECH STS conversion only; not proof of exact SKU/firmware "
            "applicability, sensor accuracy, or a calibrated measurement."
        ),
    }
