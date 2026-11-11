from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_staubli_runtime_evidence_bundle as validator  # noqa: E402


def load_inputs() -> tuple[dict, dict]:
    schema = json.loads(
        (
            ROOT / "docs/schemas/staubli-runtime-evidence-bundle.schema.json"
        ).read_text(encoding="utf-8")
    )
    bundle = json.loads(
        (
            ROOT
            / "docs/audits/2026-11-11-staubli-runtime-evidence-bundle-example-NOT_RUN.json"
        ).read_text(encoding="utf-8")
    )
    return schema, bundle


def test_example_bundle_is_valid_and_not_run() -> None:
    schema, bundle = load_inputs()
    assert validator.validate_bundle(bundle, schema) == []
    assert bundle["execution_status"] == "NOT_RUN"


def test_trace_sequence_gap_is_rejected() -> None:
    schema, bundle = load_inputs()
    bundle["event_trace"] = [
        {
            "sequence": 1,
            "logical_time_ns": 0,
            "thread_id": "t0",
            "component": "core",
            "event": "begin",
            "resource_generation": 1,
            "resource_revision": 0,
            "attempt_token": "a1",
        }
    ]
    assert any(
        "sequence" in error for error in validator.validate_bundle(bundle, schema)
    )


def test_trace_time_regression_is_rejected() -> None:
    schema, bundle = load_inputs()
    base = {
        "thread_id": "t0",
        "component": "core",
        "resource_generation": 1,
        "resource_revision": 0,
        "attempt_token": "a1",
    }
    bundle["event_trace"] = [
        dict(base, sequence=0, logical_time_ns=10, event="begin"),
        dict(base, sequence=1, logical_time_ns=9, event="end"),
    ]
    assert any(
        "moved backwards" in error
        for error in validator.validate_bundle(bundle, schema)
    )


def test_released_barrier_requires_all_participants() -> None:
    schema, bundle = load_inputs()
    bundle["harness"]["barriers"] = [
        {
            "barrier_id": "B1",
            "participants": 2,
            "released": True,
            "arrivals": ["worker-1"],
        }
    ]
    assert any(
        "released before" in error
        for error in validator.validate_bundle(bundle, schema)
    )


def test_path_traversal_is_rejected() -> None:
    schema, bundle = load_inputs()
    bundle["artifacts"] = [
        {
            "role": "test_log",
            "path": "../outside.log",
            "sha256": "0" * 64,
            "size_bytes": 0,
            "media_type": "text/plain",
        }
    ]
    assert any(
        "safe relative path" in error
        for error in validator.validate_bundle(bundle, schema)
    )


def test_run_pass_requires_complete_evidence() -> None:
    schema, bundle = load_inputs()
    bundle["execution_status"] = "RUN_PASS"
    errors = validator.validate_bundle(bundle, schema)
    assert any("RUN_PASS missing artifact roles" in error for error in errors)
    assert any("requires at least one assertion" in error for error in errors)


def test_blocked_requires_explanation() -> None:
    schema, bundle = load_inputs()
    bundle["execution_status"] = "BLOCKED"
    bundle["blockers"] = []
    assert any(
        "must contain blockers" in error
        for error in validator.validate_bundle(bundle, schema)
    )


def test_cli_writes_machine_readable_report(tmp_path: Path) -> None:
    schema, bundle = load_inputs()
    schema_path = tmp_path / "schema.json"
    bundle_path = tmp_path / "bundle.json"
    report_path = tmp_path / "report.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    result = validator.main(
        [
            "--schema",
            str(schema_path),
            "--bundle",
            str(bundle_path),
            "--report",
            str(report_path),
        ]
    )
    assert result == 0
    assert json.loads(report_path.read_text(encoding="utf-8"))["status"] == "PASS"
