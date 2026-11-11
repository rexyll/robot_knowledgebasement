from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_staubli_lifecycle_manifest as validator  # noqa: E402


@pytest.fixture
def manifest() -> dict:
    path = (
        ROOT
        / "docs/audits/2026-11-10-staubli-socket-v2-lifecycle-traceability-manifest-v1.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def schema() -> dict:
    path = ROOT / "docs/schemas/staubli-lifecycle-traceability.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_repository_manifest_passes_all_policy_checks(
    manifest: dict, schema: dict
) -> None:
    assert validator.validate_manifest(manifest, schema, ROOT) == []


def test_duplicate_record_id_is_rejected(manifest: dict, schema: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["records"][1]["id"] = broken["records"][0]["id"]
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("duplicate stable record ID" in error for error in errors)


def test_duplicate_reference_id_is_rejected(manifest: dict, schema: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["reference_catalog"].append(broken["reference_catalog"][0])
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("array items are not unique" in error for error in errors)


def test_dangling_test_reference_is_rejected(manifest: dict, schema: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["records"][0]["test_refs"].append("RACE-99")
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("dangling reference 'RACE-99'" in error for error in errors)


def test_conflicting_owner_for_same_resource_generation_is_rejected(
    manifest: dict, schema: dict
) -> None:
    broken = copy.deepcopy(manifest)
    record = next(item for item in broken["records"] if item["id"] == "PLUG-L02")
    record["resource_owner"] = "SecondSocketOwner"
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("conflicting owner/coordinator assignments" in error for error in errors)


def test_static_review_requires_source_evidence(manifest: dict, schema: dict) -> None:
    broken = copy.deepcopy(manifest)
    record = broken["records"][0]
    record["status"] = "STATIC_REVIEWED"
    record["required_evidence"] = ["design_spec", "source_review"]
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("requires PRESENT source_review" in error for error in errors)


def test_run_pass_requires_logs_environment_and_artifact_hashes(
    manifest: dict, schema: dict
) -> None:
    broken = copy.deepcopy(manifest)
    record = broken["records"][0]
    record["status"] = "RUN_PASS"
    record["required_evidence"] = ["test_log", "environment_manifest", "artifact_hash"]
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("requires PRESENT test_log" in error for error in errors)
    assert any("requires PRESENT environment_manifest" in error for error in errors)
    assert any("requires PRESENT artifact_hash" in error for error in errors)


def test_blocked_record_requires_reason(manifest: dict, schema: dict) -> None:
    broken = copy.deepcopy(manifest)
    record = broken["records"][0]
    record["status"] = "BLOCKED"
    record.pop("blocker", None)
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("missing required property 'blocker'" in error for error in errors)


def test_not_run_cannot_claim_runtime_evidence(manifest: dict, schema: dict) -> None:
    broken = copy.deepcopy(manifest)
    record = broken["records"][0]
    record["status"] = "NOT_RUN"
    record["evidence"].append(
        {
            "kind": "test_log",
            "state": "PRESENT",
            "uri": (
                "docs/audits/"
                "2026-11-10-staubli-socket-v2-lifecycle-five-axis-owner-failure-test-traceability.md"
            ),
            "sha256": "a" * 64,
        }
    )
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("NOT_RUN cannot claim PRESENT runtime evidence" in error for error in errors)


def test_schema_rejects_unknown_manifest_fields(manifest: dict, schema: dict) -> None:
    broken = copy.deepcopy(manifest)
    broken["unrecognized"] = True
    errors = validator.validate_manifest(broken, schema, ROOT)
    assert any("additional property not allowed" in error for error in errors)


def test_cli_returns_zero_and_writes_pass_report(
    manifest: dict, schema: dict, tmp_path: Path
) -> None:
    manifest_path = tmp_path / "manifest.json"
    schema_path = tmp_path / "schema.json"
    report_path = tmp_path / "report.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    code = validator.main(
        [
            "--manifest",
            str(manifest_path),
            "--schema",
            str(schema_path),
            "--report",
            str(report_path),
        ]
    )
    assert code == 0
    assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "PASS"


def test_cli_returns_one_for_policy_failure(
    manifest: dict, schema: dict, tmp_path: Path
) -> None:
    broken = copy.deepcopy(manifest)
    broken["records"][1]["id"] = broken["records"][0]["id"]
    manifest_path = tmp_path / "invalid-manifest.json"
    schema_path = tmp_path / "schema.json"
    manifest_path.write_text(json.dumps(broken), encoding="utf-8")
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    assert validator.main(["--manifest", str(manifest_path), "--schema", str(schema_path)]) == 1


def test_cli_returns_two_for_malformed_json(tmp_path: Path) -> None:
    invalid_path = tmp_path / "broken.json"
    invalid_path.write_text("{not-json", encoding="utf-8")
    assert validator.main(["--manifest", str(invalid_path)]) == 2
