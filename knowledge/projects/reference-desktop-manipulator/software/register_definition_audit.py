"""Compare the JSON read-only allowlist with a pinned rustypot STS3215 source file.

No network access and no Rust/Python servo runtime are required. Pass the
sts3215.rs file checked out from the rustypot v1.13.1 commit recorded in the
allowlist metadata.
"""
from __future__ import annotations  # noqa: I001

import argparse
import json
import re
import sys
from pathlib import Path


_REGISTER_PATTERN = re.compile(
    r"reg:\s*\(\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*,"
    r"\s*(?P<access>rw|r)\s*,\s*(?P<address>\d+)\s*,"
    r"\s*(?P<rust_type>u8|u16|u32|u64|i8|i16|i32|i64|bool)\s*,"
    r"\s*(?P<conversion>[a-zA-Z_][a-zA-Z0-9_]*|None)\s*\)"
)
_ENCODING_PATTERN = re.compile(
    r"\(\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*,\s*"
    r"(?P<encoding>unsigned|twos_complement|sign_magnitude\(\s*\d+\s*\))\s*\)"
)


class DefinitionParseError(ValueError):
    """Raised when the expected rustypot STS3215 macro data cannot be parsed."""


def parse_sts3215_definition(source: str) -> dict[str, dict[str, object]]:
    """Extract register layout, wire encoding, and conversion type from generate_servo! source."""
    if "generate_servo!(" not in source or "STS3215" not in source:
        raise DefinitionParseError("Source does not look like rustypot STS3215 definition")

    # Remove line comments before parsing so commented-out examples cannot be treated
    # as live register declarations.
    source_without_comments = re.sub(r"//[^\n]*", "", source)
    encoding_match = re.search(
        r"encoding:\s*\[(?P<body>.*?)\]\s*,\s*reg:",
        source_without_comments,
        flags=re.DOTALL,
    )
    if encoding_match is None:
        raise DefinitionParseError("Could not locate STS3215 encoding list")

    overrides: dict[str, str] = {}
    for match in _ENCODING_PATTERN.finditer(encoding_match.group("body")):
        overrides[match.group("name")] = re.sub(r"\s+", "", match.group("encoding"))

    registers: dict[str, dict[str, object]] = {}
    for match in _REGISTER_PATTERN.finditer(source_without_comments):
        name = match.group("name")
        rust_type = match.group("rust_type")
        width = 1 if rust_type in {"u8", "i8", "bool"} else int(rust_type[1:]) // 8
        if name in overrides:
            wire_encoding = overrides[name]
        elif rust_type.startswith("i"):
            wire_encoding = "twos_complement"
        else:
            wire_encoding = "unsigned"
        registers[name] = {
            "address": int(match.group("address")),
            "width_bytes": width,
            "access": "RW" if match.group("access") == "rw" else "R",
            "wire_encoding": wire_encoding,
            "rust_type": rust_type,
            "conversion": match.group("conversion"),
        }

    if not registers:
        raise DefinitionParseError("No register declarations were parsed")
    return registers


def validate_whitelist(
    whitelist: dict[str, object], definition: dict[str, dict[str, object]]
) -> list[str]:
    """Return all differences between whitelist rows and rustypot source."""
    errors: list[str] = []
    rows = whitelist.get("registers")
    if not isinstance(rows, list) or not rows:
        return ["whitelist.registers must be a non-empty list"]

    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"registers[{index}] must be an object")
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"registers[{index}].name must be a non-empty string")
            continue
        if name in seen:
            errors.append(f"{name}: duplicate whitelist entry")
            continue
        seen.add(name)
        actual = definition.get(name)
        if actual is None:
            errors.append(f"{name}: not present in rustypot STS3215 ServoDefinition")
            continue

        for key in ("address", "width_bytes", "access", "wire_encoding", "conversion"):
            expected = row.get(key)
            observed = actual[key]
            if expected != observed:
                errors.append(
                    f"{name}: {key} mismatch (whitelist={expected!r}, "
                    f"rustypot={observed!r})"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to sts3215.rs from the pinned rustypot source commit",
    )
    parser.add_argument(
        "--whitelist",
        type=Path,
        default=Path(__file__).with_name("sts3215_readonly_fields.json"),
        help="Path to the machine-readable read-only whitelist",
    )
    args = parser.parse_args(argv)

    try:
        whitelist = json.loads(args.whitelist.read_text(encoding="utf-8"))
        source = args.source.read_text(encoding="utf-8")
        definition = parse_sts3215_definition(source)
    except (OSError, json.JSONDecodeError, DefinitionParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate_whitelist(whitelist, definition)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"OK: {len(whitelist['registers'])} read-only whitelist entries match "
        "layout, wire encoding, and conversion declarations across "
        f"{len(definition)} rustypot STS3215 registers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
