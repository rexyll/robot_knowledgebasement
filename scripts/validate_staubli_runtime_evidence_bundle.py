#!/usr/bin/env python3
"""Fail-closed structural and policy checks for Stäubli Runtime Evidence Bundles."""
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
DEFAULT_EXAMPLE = ROOT / "docs/audits/2026-11-11-staubli-runtime-evidence-bundle-example-NOT_RUN.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_PASS_ROLES = {"test_log", "environment_manifest", "event_trace", "state_snapshot"}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}:{exc.lineno}:{exc.colno}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"top-level JSON value must be an object: {path}")
    return value


def validate_bundle(bundle: dict[str, Any], schema: dict[str, Any], root: Path | None = None) -> list[str]:
    errors = _check_schema_contract(schema)
    errors.extend(_schema_errors(bundle, schema, "$bundle"))
    if errors:
        return errors

    trace = bundle["event_trace"]
    previous_time = -1
    revisions: dict[tuple[str, int], int] = {}
    for index, event in enumerate(trace):
        if event["sequence"] != index:
            errors.append(f"event_trace[{index}].sequence: expected contiguous sequence {index}")
        if event["logical_time_ns"] < previous_time:
            errors.append(f"event_trace[{index}].logical_time_ns: time moved backwards")
        previous_time = event["logical_time_ns"]
        key = (event["component"], event["resource_generation"])
        previous_revision = revisions.get(key, -1)
        if event["resource_revision"] < previous_revision:
            errors.append(f"event_trace[{index}].resource_revision: revision moved backwards")
        revisions[key] = event["resource_revision"]

    for barrier in bundle["harness"]["barriers"]:
        if len(barrier["arrivals"]) > barrier["participants"]:
            errors.append(f"barrier {barrier['barrier_id']}: arrivals exceed participants")
        if barrier["released"] and len(barrier["arrivals"]) != barrier["participants"]:
            errors.append(f"barrier {barrier['barrier_id']}: released before all participants arrived")

    paths: set[str] = set()
    roles: set[str] = set()
    for artifact in bundle["artifacts"]:
        path = artifact["path"]
        if path.startswith("/") or "\\" in path or ".." in Path(path).parts:
            errors.append(f"artifact path is not a safe relative path: {path}")
            continue
        if path in paths:
            errors.append(f"duplicate artifact path: {path}")
        paths.add(path)
        roles.add(artifact["role"])
        if not SHA256_RE.fullmatch(artifact["sha256"]):
            errors.append(f"artifact {path}: invalid SHA-256")
            continue
        if root is not None:
            candidate = (root / path).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                errors.append(f"artifact path escapes bundle root: {path}")
                continue
            if not candidate.is_file():
                errors.append(f"artifact file is missing: {path}")
            else:
                digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
                if digest != artifact["sha256"]:
                    errors.append(f"artifact hash mismatch: {path}")

    status = bundle["execution_status"]
    assertions = bundle["assertions"]
    if status == "BLOCKED" and not bundle.get("blockers"):
        errors.append("BLOCKED bundle must contain blockers")
    if status == "RUN_PASS":
        if not REQUIRED_PASS_ROLES.issubset(roles):
            errors.append(f"RUN_PASS missing artifact roles: {sorted(REQUIRED_PASS_ROLES - roles)}")
        if not assertions or any(item["result"] != "PASS" for item in assertions):
            errors.append("RUN_PASS requires at least one assertion and every assertion PASS")
        if not trace or not bundle["resource_snapshots"]:
            errors.append("RUN_PASS requires non-empty event_trace and resource_snapshots")
        if any(value == "NOT_CAPTURED" for value in bundle["environment"].values()):
            errors.append("RUN_PASS environment contains NOT_CAPTURED values")
    if status == "RUN_FAIL":
        if not assertions or not any(item["result"] == "FAIL" for item in assertions):
            errors.append("RUN_FAIL requires at least one FAIL assertion")
        if "test_log" not in roles:
            errors.append("RUN_FAIL requires a test_log artifact")
    if status in {"NOT_RUN", "BLOCKED"} and assertions and any(
        item["result"] != "NOT_EVALUATED" for item in assertions
    ):
        errors.append(f"{status} bundle cannot contain evaluated assertions")
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
        "artifact_count": len(bundle.get("artifacts", [])),
        "trace_event_count": len(bundle.get("event_trace", [])),
        "error_count": len(errors),
        "errors": errors,
    }
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        except OSError as exc:
            print(f"Evidence bundle validator error: cannot write report: {exc}", file=sys.stderr)
            return 2
    if errors:
        print(f"Stäubli Runtime Evidence Bundle validation FAIL: {len(errors)} finding(s).")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Stäubli Runtime Evidence Bundle validation PASS: "
        f"{result['bundle_id']} / {result['test_id']} / {result['execution_status']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
