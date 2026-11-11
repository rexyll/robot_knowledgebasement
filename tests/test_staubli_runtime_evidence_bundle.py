from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_staubli_runtime_evidence_bundle as validator  # noqa: E402


def load_inputs() -> tuple[dict, dict]:
    schema = json.loads(
        (ROOT / "docs/schemas/staubli-runtime-evidence-bundle.schema.json").read_text(
            encoding="utf-8"
        )
    )
    bundle = json.loads(
        (
            ROOT
            / (
                (
                    "docs/audits/2026-11-11-staubli-runtime-evidence-bundle-example-NOT_RUN.json"
                )
            )
        ).read_text(encoding="utf-8")
    )
    return schema, bundle


def _write_artifact(root: Path, role: str, relative: str, data: bytes) -> dict:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "role": role,
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "media_type": (
            "application/json" if relative.endswith(".json") else "text/plain"
        ),
    }


def make_synthetic_bundle(root: Path, status: str) -> tuple[dict, dict]:
    schema, template = load_inputs()
    bundle = copy.deepcopy(template)
    bundle.update(
        {
            "bundle_id": f"SERVO-899-synthetic-{status.lower()}",
            "evidence_origin": "synthetic_fixture",
            "execution_status": status,
            "attempt": 1,
            "source_identity": {
                "repository": "rexyll/robot_knowledgebasement",
                "commit": "1" * 40,
                "upstream_repository": "ICube-Robotics/staubli_driver_ros2",
                "upstream_commit": "bd658e2d266e315d2ee35f985fb352ea88306b79",
            },
            "environment": {
                "os": "Synthetic Ubuntu 24.04 fixture",
                "architecture": "x86_64",
                "kernel": "synthetic-kernel-6.x",
                "compiler": "Synthetic GCC 13",
                "build_type": "Debug",
                "ros_distro": "Synthetic ROS 2 Jazzy",
                "dependency_lock_sha256": "a" * 64,
                "oci_image_digest": "sha256:" + "b" * 64,
            },
            "event_trace": [
                {
                    "sequence": 0,
                    "logical_time_ns": 0,
                    "thread_id": "synthetic-thread-0",
                    "component": "socket_core",
                    "event": "operation_begin",
                    "resource_generation": 1,
                    "resource_revision": 0,
                    "attempt_token": "synthetic-attempt-1",
                },
                {
                    "sequence": 1,
                    "logical_time_ns": 1,
                    "thread_id": "synthetic-thread-0",
                    "component": "socket_core",
                    "event": "operation_end",
                    "resource_generation": 1,
                    "resource_revision": 1,
                    "attempt_token": "synthetic-attempt-1",
                },
            ],
            "resource_snapshots": [
                {
                    "phase": "before",
                    "resource_id": "synthetic-resource-1",
                    "generation": 1,
                    "revision": 0,
                    "owner": "CoreControlBlock",
                    "lifecycle_state": "ACTIVE",
                    "native_handle_state": "OPEN",
                    "active_callbacks": 0,
                    "pending_handlers": 0,
                    "worker_state": "RUNNING",
                    "remote_session_state": "ACTIVE",
                },
                {
                    "phase": "after",
                    "resource_id": "synthetic-resource-1",
                    "generation": 1,
                    "revision": 1,
                    "owner": "CoreControlBlock",
                    "lifecycle_state": "STOPPED",
                    "native_handle_state": "CLOSED",
                    "active_callbacks": 0,
                    "pending_handlers": 0,
                    "worker_state": "JOINED",
                    "remote_session_state": "CLOSED",
                },
            ],
            "assertions": [
                {
                    "assertion_id": "SYNTHETIC-ASSERT-01",
                    "result": "FAIL" if status == "RUN_FAIL" else "PASS",
                    "detail": (
                        "Synthetic validator fixture; not a Stäubli execution result."
                    ),
                }
            ],
            "blockers": [],
        }
    )
    if status == "RUN_FAIL":
        failure_snapshot = copy.deepcopy(bundle["resource_snapshots"][-1])
        failure_snapshot["phase"] = "failure"
        failure_snapshot["lifecycle_state"] = "CLEANUP_FAILED"
        failure_snapshot["native_handle_state"] = "UNKNOWN"
        bundle["resource_snapshots"].append(failure_snapshot)

    environment_doc = {
        "bundle_id": bundle["bundle_id"],
        "test_id": bundle["test_id"],
        "attempt": bundle["attempt"],
        "source_identity": bundle["source_identity"],
        "environment": bundle["environment"],
    }
    trace_doc = {
        "bundle_id": bundle["bundle_id"],
        "test_id": bundle["test_id"],
        "attempt": bundle["attempt"],
        "events": bundle["event_trace"],
    }
    snapshot_doc = {
        "bundle_id": bundle["bundle_id"],
        "test_id": bundle["test_id"],
        "attempt": bundle["attempt"],
        "snapshots": bundle["resource_snapshots"],
    }
    bundle["artifacts"] = [
        _write_artifact(
            root,
            "test_log",
            "logs/test.log",
            b"SYNTHETIC VALIDATOR FIXTURE ONLY; NOT A ROBOT RUNTIME LOG.\\n",
        ),
        _write_artifact(
            root,
            "environment_manifest",
            "environment/environment.json",
            json.dumps(environment_doc, sort_keys=True).encode(),
        ),
        _write_artifact(
            root,
            "event_trace",
            "trace/events.json",
            json.dumps(trace_doc, sort_keys=True).encode(),
        ),
        _write_artifact(
            root,
            "state_snapshot",
            "snapshots/resources.json",
            json.dumps(snapshot_doc, sort_keys=True).encode(),
        ),
    ]
    return schema, bundle


def test_example_bundle_is_valid_and_not_run() -> None:
    schema, bundle = load_inputs()
    assert validator.validate_bundle(bundle, schema) == []
    assert bundle["execution_status"] == "NOT_RUN"
    assert bundle["evidence_origin"] == "synthetic_fixture"


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


def test_run_pass_requires_complete_evidence_and_bundle_root() -> None:
    schema, bundle = load_inputs()
    bundle["execution_status"] = "RUN_PASS"
    errors = validator.validate_bundle(bundle, schema)
    assert any("requires --bundle-root" in error for error in errors)
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


def test_synthetic_run_pass_fixture_verifies_all_artifacts(tmp_path: Path) -> None:
    schema, bundle = make_synthetic_bundle(tmp_path, "RUN_PASS")
    assert validator.validate_bundle(bundle, schema, tmp_path) == []


def test_synthetic_run_fail_fixture_is_valid_but_not_runtime_evidence(
    tmp_path: Path,
) -> None:
    schema, bundle = make_synthetic_bundle(tmp_path, "RUN_FAIL")
    assert validator.validate_bundle(bundle, schema, tmp_path) == []
    assert bundle["evidence_origin"] == "synthetic_fixture"


def test_artifact_hash_and_size_are_checked(tmp_path: Path) -> None:
    schema, bundle = make_synthetic_bundle(tmp_path, "RUN_PASS")
    artifact = bundle["artifacts"][0]
    (tmp_path / artifact["path"]).write_bytes(b"tampered")
    errors = validator.validate_bundle(bundle, schema, tmp_path)
    assert any("size mismatch" in error or "hash mismatch" in error for error in errors)


def test_cross_artifact_bundle_identity_is_checked(tmp_path: Path) -> None:
    schema, bundle = make_synthetic_bundle(tmp_path, "RUN_PASS")
    artifact = next(
        item for item in bundle["artifacts"] if item["role"] == "event_trace"
    )
    path = tmp_path / artifact["path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["bundle_id"] = "SERVO-000-mismatched"
    path.write_text(json.dumps(payload), encoding="utf-8")
    artifact["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    artifact["size_bytes"] = path.stat().st_size
    errors = validator.validate_bundle(bundle, schema, tmp_path)
    assert any("does not match bundle inline fields" in error for error in errors)


def test_observed_run_rejects_placeholder_environment(tmp_path: Path) -> None:
    schema, bundle = make_synthetic_bundle(tmp_path, "RUN_PASS")
    bundle["evidence_origin"] = "observed_execution"
    bundle["environment"]["kernel"] = "NOT_CAPTURED"
    errors = validator.validate_bundle(bundle, schema, tmp_path)
    assert any("placeholder" in error for error in errors)


def test_symlink_artifact_is_rejected(tmp_path: Path) -> None:
    schema, bundle = make_synthetic_bundle(tmp_path, "RUN_PASS")
    target = tmp_path / "logs/test.log"
    link = tmp_path / "logs/linked.log"
    link.symlink_to(target)
    artifact = bundle["artifacts"][0]
    artifact["path"] = "logs/linked.log"
    errors = validator.validate_bundle(bundle, schema, tmp_path)
    assert any("symbolic link" in error for error in errors)


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
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["validation_scope"] == "SYNTHETIC_FIXTURE_ONLY_NOT_RUNTIME_EVIDENCE"
