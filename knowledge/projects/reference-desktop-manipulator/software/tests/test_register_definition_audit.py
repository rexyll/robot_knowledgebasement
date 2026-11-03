from __future__ import annotations

import register_definition_audit


RUST_SOURCE = """
generate_servo!(
    STS3215, v1,
    encoding: [
        (present_position, sign_magnitude(15)),
        (present_load, sign_magnitude(10)),
    ],
    reg: (firmware_major_version, r, 0, u8, None),
    reg: (model_number, r, 3, u16, None),
    reg: (id, rw, 5, u8, None),
    reg: (present_position, r, 56, i16, AnglePosition),
    reg: (present_load, r, 60, u16, None),
    reg: (torque_enable, rw, 40, u8, bool),
);
"""


def test_parser_extracts_address_width_access_and_encoding():
    parsed = register_definition_audit.parse_sts3215_definition(RUST_SOURCE)
    assert parsed["firmware_major_version"] == {
        "address": 0,
        "width_bytes": 1,
        "access": "R",
        "wire_encoding": "unsigned",
        "rust_type": "u8",
        "conversion": "None",
    }
    assert parsed["present_position"]["wire_encoding"] == "sign_magnitude(15)"
    assert parsed["present_position"]["width_bytes"] == 2
    assert parsed["torque_enable"]["wire_encoding"] == "unsigned"


def test_parser_rejects_non_sts3215_source():
    try:
        parse_sts3215_definition("generate_servo!(OTHER, v1);")
    except register_definition_audit.DefinitionParseError as exc:
        assert "STS3215" in str(exc)
    else:
        raise AssertionError("expected DefinitionParseError")


def test_validator_accepts_matching_whitelist_subset():
    parsed = parse_sts3215_definition(RUST_SOURCE)
    whitelist = {
        "registers": [
            {
                "name": "firmware_major_version",
                "address": 0,
                "width_bytes": 1,
                "access": "R",
                "wire_encoding": "unsigned",
            },
            {
                "name": "present_position",
                "address": 56,
                "width_bytes": 2,
                "access": "R",
                "wire_encoding": "sign_magnitude(15)",
            },
        ]
    }
    assert register_definition_audit.validate_whitelist(whitelist, parsed) == []


def test_validator_reports_layout_and_encoding_mismatches():
    parsed = parse_sts3215_definition(RUST_SOURCE)
    whitelist = {
        "registers": [
            {
                "name": "present_position",
                "address": 57,
                "width_bytes": 1,
                "access": "RW",
                "wire_encoding": "unsigned",
            }
        ]
    }
    errors = validate_whitelist(whitelist, parsed)
    assert len(errors) == 4
    assert any("address mismatch" in error for error in errors)
    assert any("width_bytes mismatch" in error for error in errors)
    assert any("access mismatch" in error for error in errors)
    assert any("wire_encoding mismatch" in error for error in errors)


def test_validator_rejects_unknown_and_duplicate_fields():
    parsed = parse_sts3215_definition(RUST_SOURCE)
    row = {
        "name": "not_a_real_register",
        "address": 0,
        "width_bytes": 1,
        "access": "R",
        "wire_encoding": "unsigned",
    }
    errors = validate_whitelist({"registers": [row, row]}, parsed)
    assert any("not present" in error for error in errors)
    assert any("duplicate" in error for error in errors)
