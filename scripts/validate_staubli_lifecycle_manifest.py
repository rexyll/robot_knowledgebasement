#!/usr/bin/env python3
"""Validate the repository's Stäubli lifecycle traceability manifest.

This dependency-free validator implements the JSON Schema keyword subset used by
the checked-in schema, then applies repository-specific ownership, evidence, and
cross-reference policy checks. It is not a general-purpose JSON Schema engine.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / (
    "docs/audits/2026-11-10-staubli-socket-v2-lifecycle-traceability-manifest-v1.json"
)
DEFAULT_SCHEMA = ROOT / "docs/schemas/staubli-lifecycle-traceability.schema.json"
SUPPORTED_SCHEMA = "https://json-schema.org/draft/2020-12/schema"
SUPPORTED_KEYWORDS = {
    "$schema", "$id", "title", "description", "type", "additionalProperties",
    "required", "properties", "const", "enum", "minLength", "pattern", "minItems",
    "items", "uniqueItems", "allOf", "if", "then",
}
STATUS_REQUIREMENTS = {
    "SPECIFIED": {"design_spec"},
    "STATIC_REVIEWED": {"design_spec", "source_review"},
    "DESIGN_REVIEWED": {"design_spec", "source_review"},
    "RUN_PASS": {"test_log", "environment_manifest", "artifact_hash"},
    "RUN_FAIL": {"test_log", "environment_manifest", "artifact_hash"},
    "NOT_RUN": set(),
    "BLOCKED": set(),
}
HASH_REQUIRED_KINDS = {
    "test_log", "environment_manifest", "artifact_hash", "hardware_acceptance"
}
ID_PATTERN = re.compile(r"^(F(0[1-9]|1[0-6])|PLUG-L(0[1-9]|1[0-2]))$")
REF_PATTERN = re.compile(r"^(RACE-[0-9]{2}|EXEC-[0-9]{2})$")
HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")


def _json_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _schema_errors(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    for keyword in schema:
        if keyword not in SUPPORTED_KEYWORDS:
            errors.append(
                f"{path}: schema keyword not supported by repository validator: {keyword}"
            )
    expected = schema.get("type")
    if expected is not None and not _json_type_matches(instance, expected):
        return [f"{path}: expected {expected}, got {type(instance).__name__}"]
    if "const" in schema and _json_key(instance) != _json_key(schema["const"]):
        errors.append(f"{path}: value does not match const")
    if "enum" in schema and _json_key(instance) not in {
        _json_key(item) for item in schema["enum"]
    }:
        errors.append(f"{path}: value is not in enum")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: string shorter than minLength={schema['minLength']}")
        pattern = schema.get("pattern")
        if pattern and re.search(pattern, instance) is None:
            errors.append(f"{path}: string does not match pattern {pattern!r}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: array shorter than minItems={schema['minItems']}")
        if schema.get("uniqueItems"):
            keys = [_json_key(item) for item in instance]
            if len(keys) != len(set(keys)):
                errors.append(f"{path}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(_schema_errors(item, item_schema, f"{path}[{index}]"))
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    errors.append(f"{path}: additional property not allowed: {key!r}")
        for key, child_schema in properties.items():
            if key in instance:
                errors.extend(_schema_errors(instance[key], child_schema, f"{path}.{key}"))
    for child_schema in schema.get("allOf", []):
        errors.extend(_schema_errors(instance, child_schema, path))
    conditional = schema.get("if")
    if conditional is not None and not _schema_errors(instance, conditional, path):
        then_schema = schema.get("then")
        if isinstance(then_schema, dict):
            errors.extend(_schema_errors(instance, then_schema, path))
    return errors


def _check_schema_contract(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if schema.get("$schema") != SUPPORTED_SCHEMA:
        errors.append(f"schema: expected Draft 2020-12 declaration {SUPPORTED_SCHEMA}")
    if not schema.get("$id"):
        errors.append("schema: missing stable $id")

    def walk(node: Any, path: str = "schema") -> None:
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key not in SUPPORTED_KEYWORDS:
                errors.append(f"{path}: unsupported JSON Schema keyword {key!r}")
            if key == "properties" and isinstance(value, dict):
                for property_name, child in value.items():
                    walk(child, f"{path}.properties.{property_name}")
            elif key in {"items", "if", "then"} and isinstance(value, dict):
                walk(value, f"{path}.{key}")
            elif key == "allOf" and isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, f"{path}.allOf[{index}]")

    walk(schema)
    return errors


def validate_manifest(
    manifest: dict[str, Any], schema: dict[str, Any], repo_root: Path = ROOT
) -> list[str]:
    errors = _check_schema_contract(schema)
    errors.extend(_schema_errors(manifest, schema))
    if errors:
        return errors

    reference_set = set(manifest["reference_catalog"])
    records = manifest["records"]
    seen_ids: set[str] = set()
    ownership_groups: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)

    for index, record in enumerate(records):
        location = f"records[{index}]"
        record_id = record["id"]
        if not ID_PATTERN.fullmatch(record_id):
            errors.append(f"{location}.id: invalid stable record ID {record_id!r}")
        if record_id in seen_ids:
            errors.append(f"{location}.id: duplicate stable record ID {record_id}")
        seen_ids.add(record_id)

        for reference in record["test_refs"]:
            if not REF_PATTERN.fullmatch(reference):
                errors.append(f"{location}.test_refs: invalid test reference {reference!r}")
            if reference not in reference_set:
                errors.append(f"{location}.test_refs: dangling reference {reference!r}")

        owner = record["resource_owner"].strip()
        coordinator = record["reconcile_coordinator"].strip()
        if not owner:
            errors.append(f"{location}.resource_owner: owner must not be blank")
        if not coordinator:
            errors.append(f"{location}.reconcile_coordinator: coordinator must not be blank")
        group_key = (record["resource_key"], record["ownership_phase"])
        ownership_groups[group_key].add((owner, coordinator))

        evidence_by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for evidence in record["evidence"]:
            evidence_by_kind[evidence["kind"]].append(evidence)
            uri = evidence["uri"]
            if not uri.startswith(("https://", "http://")):
                candidate = (repo_root / uri).resolve()
                root = repo_root.resolve()
                if root not in candidate.parents and candidate != root:
                    errors.append(f"{location}.evidence: URI escapes repository root: {uri!r}")
                elif evidence["state"] == "PRESENT" and not candidate.is_file():
                    errors.append(
                        f"{location}.evidence: PRESENT repository file does not exist: {uri!r}"
                    )
            if evidence["kind"] in HASH_REQUIRED_KINDS:
                if not HASH_PATTERN.fullmatch(evidence.get("sha256", "")):
                    errors.append(
                        f"{location}.evidence: {evidence['kind']} requires a lowercase SHA-256"
                    )
            elif "sha256" in evidence and not HASH_PATTERN.fullmatch(evidence["sha256"]):
                errors.append(
                    f"{location}.evidence: invalid SHA-256 for {evidence['kind']}"
                )

        status = record["status"]
        required_by_status = STATUS_REQUIREMENTS[status]
        required_in_record = set(record["required_evidence"])
        missing_contract = required_by_status - required_in_record
        if missing_contract:
            errors.append(
                f"{location}.required_evidence: status {status} omits "
                f"{sorted(missing_contract)}"
            )
        for kind in required_by_status:
            if not any(
                item["state"] == "PRESENT" for item in evidence_by_kind.get(kind, [])
            ):
                errors.append(f"{location}.evidence: status {status} requires PRESENT {kind}")

        if status in {"RUN_PASS", "RUN_FAIL"}:
            if not record["test_refs"]:
                errors.append(
                    f"{location}.test_refs: {status} requires at least one test reference"
                )
        if status == "NOT_RUN" and any(
            item["kind"] in {"test_log", "environment_manifest", "hardware_acceptance"}
            and item["state"] == "PRESENT"
            for item in record["evidence"]
        ):
            errors.append(
                f"{location}.evidence: NOT_RUN cannot claim PRESENT runtime evidence"
            )
        if status == "BLOCKED" and not record.get("blocker", "").strip():
            errors.append(f"{location}.blocker: BLOCKED record requires a non-empty blocker")

    for group_key, assignments in ownership_groups.items():
        if len(assignments) != 1:
            errors.append(
                "ownership: conflicting owner/coordinator assignments for "
                f"resource_key={group_key[0]!r}, phase={group_key[1]!r}: "
                f"{sorted(assignments)}"
            )
    return errors


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"invalid JSON in {path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"top-level JSON value must be an object: {path}")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--report", type=Path, help="Optional machine-readable JSON result path")
    args = parser.parse_args(argv)
    try:
        manifest = _load_json(args.manifest)
        schema = _load_json(args.schema)
        errors = validate_manifest(manifest, schema, ROOT)
    except RuntimeError as exc:
        print(f"Validator error: {exc}", file=sys.stderr)
        return 2

    result = {
        "schema_version": "1.0.0",
        "validator": "repository-json-schema-subset-and-policy-validator",
        "status": "PASS" if not errors else "FAIL",
        "record_count": len(manifest.get("records", [])),
        "reference_count": len(manifest.get("reference_catalog", [])),
        "error_count": len(errors),
        "errors": errors,
    }
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"Validator error: cannot write report {args.report}: {exc}", file=sys.stderr)
            return 2
    if errors:
        print(f"Stäubli traceability validation FAIL: {len(errors)} finding(s).")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Stäubli traceability validation PASS: "
        f"{result['record_count']} records, {result['reference_count']} references."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
