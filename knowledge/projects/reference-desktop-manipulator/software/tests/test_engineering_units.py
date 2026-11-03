from __future__ import annotations  # noqa: I001

import pytest

from engineering_units import convert_decoded_reading


@pytest.mark.parametrize(
    ("field", "decoded", "expected", "unit"),
    [
        ("present_load", 250, 25.0, "%"),
        ("present_load", -250, -25.0, "%"),
        ("present_voltage", 74, 7.4, "V"),
        ("present_temperature", 63, 63, "degC"),
        ("present_current", 100, 0.65, "A"),
    ],
)
def test_converts_documented_generic_sts_units(field, decoded, expected, unit):
    result = convert_decoded_reading(field, decoded)

    assert result["register_value_decoded"] == decoded
    assert result["engineering_value"] == pytest.approx(expected)
    assert result["engineering_unit"] == unit
    assert result["calibration_status"] == "not_calibrated"
    assert result["source_url"].startswith("https://www.feetech.cn/")


def test_load_conversion_preserves_signed_decoded_count():
    positive = convert_decoded_reading("present_load", 321)
    negative = convert_decoded_reading("present_load", -321)

    assert positive["register_value_decoded"] == 321
    assert negative["register_value_decoded"] == -321
    assert positive["engineering_value"] == 32.1
    assert negative["engineering_value"] == -32.1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("present_load", -1024),
        ("present_load", 1024),
        ("present_voltage", -1),
        ("present_voltage", 256),
        ("present_temperature", 256),
        ("present_current", -1),
        ("present_current", 65536),
    ],
)
def test_rejects_values_outside_register_range(field, value):
    with pytest.raises(ValueError):
        convert_decoded_reading(field, value)


@pytest.mark.parametrize("field", ["present_position", "present_speed", "unknown"])
def test_does_not_guess_unapproved_conversions(field):
    with pytest.raises(ValueError, match="No approved"):
        convert_decoded_reading(field, 10)


@pytest.mark.parametrize("value", [True, False, 1.5, "74", None])
def test_rejects_non_integer_decoded_values(value):
    with pytest.raises(TypeError):
        convert_decoded_reading("present_voltage", value)


def test_flags_values_beyond_generic_nominal_ranges_without_clipping():
    load = convert_decoded_reading("present_load", 1001)
    current = convert_decoded_reading("present_current", 501)

    assert load["engineering_value"] == pytest.approx(100.1)
    assert current["engineering_value"] == pytest.approx(3.2565)
    assert load["outside_documented_nominal_range"] is True
    assert current["outside_documented_nominal_range"] is True
