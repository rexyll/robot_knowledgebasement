from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_staubli_test_case_catalog as validator  # noqa: E402


@pytest.fixture
def inputs() -> tuple[dict, dict, dict, dict]:
    manifest = json.loads(
        (ROOT / "docs/audits/2026-11-10-staubli-socket-v2-lifecycle-traceability-manifest-v1.json").read_text(encoding="utf-8")
    )
    manifest_schema = json.loads(
        (ROOT / "docs/schemas/staubli-lifecycle-traceability.schema.json").read_text(encoding="utf-8")
    )
    catalog = json.loads(
        (ROOT / "docs/audits/2026-11-11-staubli-socket-v2-race-exec-test-case-catalog-v1.json").read_text(encoding="utf-8")
    )
    catalog_schema = json.loads(
        (ROOT / "docs/schemas/staubli-race-exec-test-case-catalog.schema.json").read_text(encoding="utf-8")
    )
    return manifest, manifest_schema, catalog, catalog_schema


def test_canonical_catalog_has_complete_bidirectional_mapping(inputs: tuple) -> None:
    assert validator.validate_catalog(*inputs) == []


def test_missing_catalog_case_is_rejected(inputs: tuple) -> None:
    manifest, manifest_schema, catalog, catalog_schema = copy.deepcopy(inputs)
    catalog["test_cases"] = [
        case for case in catalog["test_cases"] if case["test_id"] != "RACE-16"
    ]
    errors = validator.validate_catalog(manifest, manifest_schema, catalog, catalog_schema)
    assert any("catalog.test_cases" in error for error in errors)


def test_manifest_reference_without_record_mapping_is_rejected(inputs: tuple) -> None:
    manifest, manifest_schema, catalog, catalog_schema = copy.deepcopy(inputs)
    for record in manifest["records"]:
        record["test_refs"] = [ref for ref in record["test_refs"] if ref != "EXEC-02"]
    for case in catalog["test_cases"]:
        if case["test_id"] == "EXEC-02":
            case["manifest_record_ids"] = []
    # The catalog schema rejects empty reverse mappings before policy checks.
    errors = validator.validate_catalog(manifest, manifest_schema, catalog, catalog_schema)
    assert any("minItems" in error or "not used by any record" in error for error in errors)


def test_catalog_reverse_mapping_must_match_manifest(inputs: tuple) -> None:
    manifest, manifest_schema, catalog, catalog_schema = copy.deepcopy(inputs)
    case = next(item for item in catalog["test_cases"] if item["test_id"] == "RACE-07")
    case["manifest_record_ids"].remove("F01")
    errors = validator.validate_catalog(manifest, manifest_schema, catalog, catalog_schema)
    assert any("RACE-07 mapping differs" in error for error in errors)


def test_catalog_cannot_claim_test_execution(inputs: tuple) -> None:
    manifest, manifest_schema, catalog, catalog_schema = copy.deepcopy(inputs)
    case = catalog["test_cases"][0]
    case["execution_state"] = "RUN_PASS"
    errors = validator.validate_catalog(manifest, manifest_schema, catalog, catalog_schema)
    assert any("const" in error or "execution_state" in error for error in errors)


def test_unknown_manifest_record_in_reverse_mapping_is_rejected(inputs: tuple) -> None:
    manifest, manifest_schema, catalog, catalog_schema = copy.deepcopy(inputs)
    catalog["test_cases"][0]["manifest_record_ids"].append("F99")
    errors = validator.validate_catalog(manifest, manifest_schema, catalog, catalog_schema)
    assert any("unknown manifest record F99" in error for error in errors)


def test_catalog_and_manifest_reference_sets_must_match(inputs: tuple) -> None:
    manifest, manifest_schema, catalog, catalog_schema = copy.deepcopy(inputs)
    catalog["reference_catalog"].remove("EXEC-04")
    errors = validator.validate_catalog(manifest, manifest_schema, catalog, catalog_schema)
    assert any("reference_catalog" in error for error in errors)


def test_cli_returns_zero_and_writes_report(inputs: tuple, tmp_path: Path) -> None:
    manifest, manifest_schema, catalog, catalog_schema = inputs
    files = {
        "manifest.json": manifest,
        "manifest-schema.json": manifest_schema,
        "catalog.json": catalog,
        "catalog-schema.json": catalog_schema,
    }
    paths = {}
    for name, value in files.items():
        path = tmp_path / name
        path.write_text(json.dumps(value), encoding="utf-8")
        paths[name] = path
    report = tmp_path / "report.json"
    code = validator.main([
        "--manifest", str(paths["manifest.json"]),
        "--manifest-schema", str(paths["manifest-schema.json"]),
        "--catalog", str(paths["catalog.json"]),
        "--catalog-schema", str(paths["catalog-schema.json"]),
        "--report", str(report),
    ])
    assert code == 0
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "PASS"


def test_cli_returns_one_for_reverse_mapping_failure(inputs: tuple, tmp_path: Path) -> None:
    manifest, manifest_schema, catalog, catalog_schema = copy.deepcopy(inputs)
    catalog["test_cases"][0]["manifest_record_ids"].remove("F01")
    paths = []
    for name, value in [
        ("manifest.json", manifest),
        ("manifest-schema.json", manifest_schema),
        ("catalog.json", catalog),
        ("catalog-schema.json", catalog_schema),
    ]:
        path = tmp_path / name
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(path)
    assert validator.main([
        "--manifest", str(paths[0]),
        "--manifest-schema", str(paths[1]),
        "--catalog", str(paths[2]),
        "--catalog-schema", str(paths[3]),
    ]) == 1
