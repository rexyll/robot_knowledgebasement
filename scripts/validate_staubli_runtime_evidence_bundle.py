#!/usr/bin/env python3
"""Fail-closed validation for Stäubli Runtime Evidence Bundles."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_staubli_lifecycle_manifest import _check_schema_contract, _schema_errors

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs/schemas/staubli-runtime-evidence-bundle.schema.json"
DEFAULT_EXAMPLE = ROOT / (
    "docs/audits/2026-11-11-staubli-runtime-evidence-bundle-example-NOT_RUN.json"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_PASS_ROLES = {
    "test_log",
    "environment_manifest",
    "event_trace",
    "state_snapshot",
}
PLACEHOLDERS = {"", "NOT_CAPTURED", "UNKNOWN", "UNSET"}


def load_json(path: Path) -> dict[str, Any]:
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


def _safe_artifact_path(root: Path, relative: str) -> tuple[Path | None, str | None]:
    rel = Path(relative)
    path_parts = relative.split("/")
    if (
        rel.is_absolute()
        or "\\" in relative
        or not relative
        or any(part in {"", ".", ".."} for part in path_parts)
    ):
        return None, f"artifact path is not a normalized safe relative path: {relative}"
    candidate = root / rel
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            return None, f"artifact path contains a symbolic link: {relative}"
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None, f"artifact path escapes bundle root: {relative}"
    return resolved, None


def _environment_errors(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    identity = bundle["source_identity"]
    if identity["commit"] == "0" * 40 or identity["upstream_commit"] == "0" * 40:
        errors.append("source_identity contains a placeholder all-zero commit")
    environment = bundle["environment"]
    for key, value in environment.items():
        if isinstance(value, str) and value in PLACEHOLDERS:
            errors.append(f"environment.{key} is a placeholder: {value!r}")
    for key in ("dependency_lock_sha256",):
        if environment[key] == "0" * 64:
            errors.append(f"environment.{key} is a placeholder all-zero digest")
    if environment["oci_image_digest"] == "sha256:" + "0" * 64:
        errors.append("environment.oci_image_digest is a placeholder all-zero digest")
    return errors


def validate_bundle(
    bundle: dict[str, Any],
    schema: dict[str, Any],
    root: Path | None = None,
) -> list[str]:
    errors = _check_schema_contract(schema)
    errors.extend(_schema_errors(bundle, schema, "$bundle"))
    if errors:
        return errors

    if bundle["attempt"] < 1:
        errors.append("attempt must be a positive integer")

    trace = bundle["event_trace"]
    previous_time = -1
    revisions: dict[tuple[str, int], int] = {}
    for index, event in enumerate(trace):
        if event["sequence"] != index:
            errors.append(
                f"event_trace[{index}].sequence: expected contiguous sequence {index}"
            )
        if event["logical_time_ns"] < previous_time:
            errors.append(f"event_trace[{index}].logical_time_ns: time moved backwards")
        previous_time = event["logical_time_ns"]
        key = (event["component"], event["resource_generation"])
        previous_revision = revisions.get(key, -1)
        if event["resource_revision"] < previous_revision:
            errors.append(
                f"event_trace[{index}].resource_revision: revision moved backwards"
            )
        revisions[key] = event["resource_revision"]

    attempt_tokens = {event["attempt_token"] for event in trace}
    if len(attempt_tokens) > 1:
        errors.append(
            "event_trace contains multiple attempt_token values for one bundle"
        )

    for barrier in bundle["harness"]["barriers"]:
        if len(barrier["arrivals"]) > barrier["participants"]:
            errors.append(
                f"barrier {barrier['barrier_id']}: arrivals exceed participants"
            )
        if barrier["released"] and len(barrier["arrivals"]) != barrier["participants"]:
            errors.append(
                f"barrier {barrier['barrier_id']}: released before "
                "all participants arrived"
            )

    paths: set[str] = set()
    roles: dict[str, dict[str, Any]] = {}
    for artifact in bundle["artifacts"]:
        relative = artifact["path"]
        if relative in paths:
            errors.append(f"duplicate artifact path: {relative}")
        paths.add(relative)
        if artifact["role"] in roles:
            errors.append(f"duplicate artifact role: {artifact['role']}")
        roles[artifact["role"]] = artifact
        if not SHA256_RE.fullmatch(artifact["sha256"]):
            errors.append(f"artifact {relative}: invalid SHA-256")
        if root is not None:
            candidate, path_error = _safe_artifact_path(root, relative)
            if path_error:
                errors.append(path_error)
                continue
            assert candidate is not None
            if not candidate.is_file():
                errors.append(f"artifact file is missing: {relative}")
                continue
            data = candidate.read_bytes()
            if len(data) != artifact["size_bytes"]:
                errors.append(
                    f"artifact size mismatch: {relative} "
                    f"(declared {artifact['size_bytes']}, actual {len(data)})"
                )
            digest = hashlib.sha256(data).hexdigest()
            if digest != artifact["sha256"]:
                errors.append(f"artifact hash mismatch: {relative}")

    status = bundle["execution_status"]
    assertions = bundle["assertions"]
    if status == "BLOCKED" and not bundle.get("blockers"):
        errors.append("BLOCKED bundle must contain blockers")
    if status in {"NOT_RUN", "BLOCKED"} and assertions and any(
        item["result"] != "NOT_EVALUATED" for item in assertions
    ):
        errors.append(f"{status} bundle cannot contain evaluated assertions")
    if status == "RUN_PASS":
        missing_roles = REQUIRED_PASS_ROLES - set(roles)
        if missing_roles:
            errors.append(f"RUN_PASS missing artifact roles: {sorted(missing_roles)}")
        if not assertions or any(item["result"] != "PASS" for item in assertions):
            errors.append(
                "RUN_PASS requires at least one assertion and every assertion PASS"
            )
        if not trace or not bundle["resource_snapshots"]:
            errors.append(
                "RUN_PASS requires non-empty event_trace and resource_snapshots"
            )
        phases = {snapshot["phase"] for snapshot in bundle["resource_snapshots"]}
        if not {"before", "after"}.issubset(phases):
            errors.append("RUN_PASS requires before and after resource snapshots")
        errors.extend(_environment_errors(bundle))
        if any(
            any(
                token in str(snapshot[field]).upper()
                for token in ("UNKNOWN", "RESIDUAL")
            )
            for snapshot in bundle["resource_snapshots"]
            for field in (
                "owner",
                "lifecycle_state",
                "native_handle_state",
                "worker_state",
                "remote_session_state",
            )
        ):
            errors.append("RUN_PASS contains UNKNOWN/RESIDUAL resource state")
        if "failure" in {
            snapshot["phase"] for snapshot in bundle["resource_snapshots"]
        }:
            errors.append("RUN_PASS cannot contain a failure-phase resource snapshot")
    if status == "RUN_FAIL":
        if not assertions or not any(item["result"] == "FAIL" for item in assertions):
            errors.append("RUN_FAIL requires at least one FAIL assertion")
        if "test_log" not in roles:
            errors.append("RUN_FAIL requires a test_log artifact")
        if not trace:
            errors.append("RUN_FAIL requires a non-empty event_trace")
        phases = {snapshot["phase"] for snapshot in bundle["resource_snapshots"]}
        if not {"before", "failure"}.issubset(phases):
            errors.append("RUN_FAIL requires before and failure resource snapshots")

    if root is not None:
        for role, expected in (
            ("environment_manifest", {
                "bundle_id": bundle["bundle_id"],
                "test_id": bundle["test_id"],
                "attempt": bundle["attempt"],
                "source_identity": bundle["source_identity"],
                "environment": bundle["environment"],
            }),
            ("event_trace", {
                "bundle_id": bundle["bundle_id"],
                "test_id": bundle["test_id"],
                "attempt": bundle["attempt"],
                "events": bundle["event_trace"],
            }),
            ("state_snapshot", {
                "bundle_id": bundle["bundle_id"],
                "test_id": bundle["test_id"],
                "attempt": bundle["attempt"],
                "snapshots": bundle["resource_snapshots"],
            }),
        ):
            artifact = roles.get(role)
            if artifact is None:
                continue
            candidate, path_error = _safe_artifact_path(root, artifact["path"])
            if path_error or candidate is None or not candidate.is_file():
                continue
            try:
                actual = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"{role} artifact is not readable JSON: {exc}")
                continue
            if actual != expected:
                errors.append(f"{role} artifact does not match bundle inline fields")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_EXAMPLE)
    parser.add_argument("--bundle-root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        schema = load_json(args.schema)
        bundle = load_json(args.bundle)
        errors = validate_bundle(bundle, schema, args.bundle_root)
    except RuntimeError as exc:
        print(f"Evidence bundle validator error: {exc}", file=sys.stderr)
        return 2
    result = {
        "schema_version": "1.0.0",
        "validator": "staubli-runtime-evidence-bundle-validator",
        "status": "PASS" if not errors else "FAIL",
        "bundle_id": bundle.get("bundle_id"),
        "test_id": bundle.get("test_id"),
        "execution_status": bundle.get("execution_status"),
        "evidence_origin": bundle.get("evidence_origin"),
        "validation_scope": (
            "SYNTHETIC_FIXTURE_ONLY_NOT_RUNTIME_EVIDENCE"
            if bundle.get("evidence_origin") == "synthetic_fixture"
            else "OBSERVED_EXECUTION_EVIDENCE"
        ),
        "artifact_count": len(bundle.get("artifacts", [])),
        "trace_event_count": len(bundle.get("event_trace", [])),
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
                f"Evidence bundle validator error: cannot write report: {exc}",
                file=sys.stderr,
            )
            return 2
    if errors:
        print(
            "Stäubli Runtime Evidence Bundle validation FAIL: "
            f"{len(errors)} finding(s)."
        )
        for error in errors:
            print(f"- {error}")
        return 1
    scope_note = (
        " SYNTHETIC FIXTURE ONLY — NOT RUNTIME EVIDENCE."
        if bundle.get("evidence_origin") == "synthetic_fixture"
        else ""
    )
    print(
        "Stäubli Runtime Evidence Bundle validation PASS: "
        f"{result['bundle_id']} / {result['test_id']} / "
        f"{result['execution_status']}.{scope_note}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
