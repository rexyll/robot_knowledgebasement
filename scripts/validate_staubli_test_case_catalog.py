#!/usr/bin/env python3
"""Validate bidirectional integrity between the Stäubli manifest and RACE/EXEC catalog."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_staubli_lifecycle_manifest import (
    _check_schema_contract,
    _schema_errors,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / (
    "docs/audits/2026-11-10-staubli-socket-v2-lifecycle-traceability-manifest-v1.json"
)
DEFAULT_MANIFEST_SCHEMA = ROOT / "docs/schemas/staubli-lifecycle-traceability.schema.json"
DEFAULT_CATALOG = ROOT / (
    "docs/audits/2026-11-11-staubli-socket-v2-race-exec-test-case-catalog-v1.json"
)
DEFAULT_CATALOG_SCHEMA = ROOT / (
    "docs/schemas/staubli-race-exec-test-case-catalog.schema.json"
)
EXPECTED_IDS = {
    *(f"RACE-{number:02d}" for number in range(1, 17)),
    *(f"EXEC-{number:02d}" for number in range(1, 5)),
}
RECORD_ID_PATTERN = re.compile(r"^(F(0[1-9]|1[0-6])|PLUG-L(0[1-9]|1[0-2]))$")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"invalid JSON in {path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"top-level JSON value must be an object: {path}")
    return value


def validate_catalog(
    manifest: dict[str, Any],
    manifest_schema: dict[str, Any],
    catalog: dict[str, Any],
    catalog_schema: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    errors.extend(_check_schema_contract(manifest_schema))
    errors.extend(_check_schema_contract(catalog_schema))
    errors.extend(_schema_errors(manifest, manifest_schema, "$manifest"))
    errors.extend(_schema_errors(catalog, catalog_schema, "$catalog"))
    if errors:
        return errors

    manifest_refs = set(manifest["reference_catalog"])
    catalog_refs = set(catalog["reference_catalog"])
    if manifest_refs != EXPECTED_IDS:
        errors.append(
            "manifest.reference_catalog: must equal the complete RACE-01..16 and EXEC-01..04 set"
        )
    if catalog_refs != EXPECTED_IDS:
        errors.append(
            "catalog.reference_catalog: must equal the complete RACE-01..16 and EXEC-01..04 set"
        )
    if manifest_refs != catalog_refs:
        errors.append(
            "cross_reference: manifest and catalog reference catalogs differ"
        )

    manifest_records = {record["id"]: record for record in manifest["records"]}
    cases = catalog["test_cases"]
    case_ids = [case["test_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("catalog.test_cases: duplicate test_id")
    case_map = {case["test_id"]: case for case in cases}
    if set(case_map) != EXPECTED_IDS:
        errors.append(
            "catalog.test_cases: IDs must exactly cover RACE-01..16 and EXEC-01..04"
        )

    manifest_reverse: dict[str, set[str]] = {reference: set() for reference in manifest_refs}
    for record_id, record in manifest_records.items():
        for reference in record["test_refs"]:
            if reference not in manifest_refs:
                errors.append(
                    f"manifest.records[{record_id}].test_refs: unknown reference {reference}"
                )
                continue
            manifest_reverse[reference].add(record_id)

    catalog_reverse: dict[str, set[str]] = {}
    for test_id, case in case_map.items():
        declared = case["manifest_record_ids"]
        if len(declared) != len(set(declared)):
            errors.append(f"catalog.{test_id}.manifest_record_ids: duplicate record ID")
        unknown = set(declared) - set(manifest_records)
        for record_id in sorted(unknown):
            errors.append(
                f"catalog.{test_id}.manifest_record_ids: unknown manifest record {record_id}"
            )
        catalog_reverse[test_id] = set(declared)
        for record_id in declared:
            if (
                record_id in manifest_records
                and test_id not in manifest_records[record_id]["test_refs"]
            ):
                errors.append(
                    f"cross_reference: catalog {test_id} names {record_id}, "
                    "but manifest record does not reference the test"
                )

    for reference in sorted(manifest_refs & catalog_refs):
        manifest_ids = manifest_reverse.get(reference, set())
        catalog_ids = catalog_reverse.get(reference, set())
        if not manifest_ids:
            errors.append(
                f"cross_reference: manifest reference {reference} is not used by any record"
            )
        if not catalog_ids:
            errors.append(
                f"cross_reference: catalog case {reference} has no manifest records"
            )
        if manifest_ids != catalog_ids:
            errors.append(
                f"cross_reference: {reference} mapping differs; "
                f"manifest={sorted(manifest_ids)}, catalog={sorted(catalog_ids)}"
            )

    for case in cases:
        if case["execution_state"] != "NOT_RUN":
            errors.append(
                f"catalog.{case['test_id']}.execution_state: design catalog must remain NOT_RUN"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--manifest-schema", type=Path, default=DEFAULT_MANIFEST_SCHEMA)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--catalog-schema", type=Path, default=DEFAULT_CATALOG_SCHEMA)
    parser.add_argument("--report", type=Path, help="Optional machine-readable JSON report")
    args = parser.parse_args(argv)
    try:
        manifest = _load_json(args.manifest)
        manifest_schema = _load_json(args.manifest_schema)
        catalog = _load_json(args.catalog)
        catalog_schema = _load_json(args.catalog_schema)
        errors = validate_catalog(manifest, manifest_schema, catalog, catalog_schema)
    except RuntimeError as exc:
        print(f"Catalog validator error: {exc}", file=sys.stderr)
        return 2

    result = {
        "schema_version": "1.0.0",
        "validator": "staubli-manifest-catalog-bidirectional-validator",
        "status": "PASS" if not errors else "FAIL",
        "manifest_record_count": len(manifest.get("records", [])),
        "catalog_case_count": len(catalog.get("test_cases", [])),
        "reference_count": len(catalog.get("reference_catalog", [])),
        "execution_state_counts": {
            "NOT_RUN": sum(
                case.get("execution_state") == "NOT_RUN"
                for case in catalog.get("test_cases", [])
            )
        },
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
            print(
                f"Catalog validator error: cannot write report {args.report}: {exc}",
                file=sys.stderr,
            )
            return 2
    if errors:
        print(f"Stäubli RACE/EXEC catalog validation FAIL: {len(errors)} finding(s).")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Stäubli RACE/EXEC catalog validation PASS: "
        f"{result['manifest_record_count']} manifest records, "
        f"{result['catalog_case_count']} cases, "
        f"{result['reference_count']} references; all NOT_RUN."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
