#!/usr/bin/env python3
"""Validate normalized CMake File API snapshots for Stäubli Fake Harness isolation.

This validator consumes normalized snapshots exported by a separate CMake File API
collector. It does not claim to compile C++ or inspect a live build tree itself.
"""
from __future__ import annotations  # noqa: I001

import argparse
import json
import sys
from pathlib import Path
from typing import Any


FORBIDDEN_TOKENS = (
    "staubli_socket_test_support",
    "FakeClock",
    "DeterministicBarrier",
    "DeterministicLatch",
    "DeterministicExecutor",
    "FaultInjector",
    "FaultScript",
)
DEFAULT_PRODUCTION = ("staubli_socket_core", "staubli_driver_plugin")
DEFAULT_TEST = ("staubli_socket_test_support", "staubli_socket_unit_tests")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return value


def target_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    targets = snapshot.get("targets")
    if not isinstance(targets, list):
        raise ValueError("snapshot.targets must be an array")
    result: dict[str, dict[str, Any]] = {}
    for item in targets:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("each target must be an object with a string name")
        name = item["name"]
        if name in result:
            raise ValueError(f"duplicate target: {name}")
        result[name] = item
    return result


def transitive_closure(
    targets: dict[str, dict[str, Any]],
    roots: list[str],
) -> set[str]:
    seen: set[str] = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        target = targets.get(name)
        if target is None:
            continue
        dependencies = target.get("dependencies", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(item, str) for item in dependencies
        ):
            raise ValueError(f"{name}.dependencies must be an array of strings")
        pending.extend(dependencies)
    return seen


def validate(args: argparse.Namespace) -> dict[str, Any]:
    off = load_json(args.build_off)
    on = load_json(args.build_on)
    off_targets = target_map(off)
    on_targets = target_map(on)
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(check_id: str, passed: bool, detail: str) -> None:
        checks.append(
            {
                "id": check_id,
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )
        if not passed:
            errors.append(f"{check_id}: {detail}")

    for name in args.production_target:
        check(
            "PROD-OFF-" + name,
            name in off_targets,
            f"{name} must exist with BUILD_TESTING=OFF",
        )
        check(
            "PROD-ON-" + name,
            name in on_targets,
            f"{name} must exist with BUILD_TESTING=ON",
        )

    for name in args.test_target:
        check(
            "TEST-OFF-" + name,
            name not in off_targets,
            f"{name} must not exist with BUILD_TESTING=OFF",
        )
        check(
            "TEST-ON-" + name,
            name in on_targets,
            f"{name} must exist with BUILD_TESTING=ON",
        )

    production_closure = transitive_closure(
        on_targets,
        list(args.production_target),
    )
    forbidden = sorted(
        name
        for name in production_closure
        if any(token.casefold() in name.casefold() for token in FORBIDDEN_TOKENS)
    )
    check(
        "PROD-CLOSURE-ZERO-FAKE",
        not forbidden,
        "forbidden test components in production closure: "
        + (", ".join(forbidden) or "none"),
    )

    install_entries = on.get("install_entries", [])
    if not isinstance(install_entries, list) or any(
        not isinstance(item, str) for item in install_entries
    ):
        raise ValueError("build_on.install_entries must be an array of strings")
    leaked_install = sorted(
        item
        for item in install_entries
        if any(token.casefold() in item.casefold() for token in FORBIDDEN_TOKENS)
    )
    check(
        "INSTALL-ZERO-FAKE",
        not leaked_install,
        "test components in install manifest: "
        + (", ".join(leaked_install) or "none"),
    )

    exports = on.get("exported_targets", [])
    if not isinstance(exports, list) or any(
        not isinstance(item, str) for item in exports
    ):
        raise ValueError("build_on.exported_targets must be an array of strings")
    leaked_exports = sorted(
        item
        for item in exports
        if any(token.casefold() in item.casefold() for token in FORBIDDEN_TOKENS)
    )
    check(
        "EXPORT-ZERO-FAKE",
        not leaked_exports,
        "test components in exported targets: "
        + (", ".join(leaked_exports) or "none"),
    )

    plugin = on_targets.get(args.plugin_target)
    plugin_closure = transitive_closure(on_targets, [args.plugin_target])
    plugin_leaks = sorted(
        name
        for name in plugin_closure
        if any(token.casefold() in name.casefold() for token in FORBIDDEN_TOKENS)
    )
    check(
        "PLUGIN-ZERO-FAKE",
        plugin is not None and not plugin_leaks,
        "plugin closure test-component matches: "
        + (", ".join(plugin_leaks) or "none"),
    )

    return {
        "schema_version": "1.0.0",
        "validator": "validate_staubli_fake_harness_target_graph",
        "validation_scope": "normalized_cmake_target_and_install_export_snapshot_only",
        "execution_status": "PASS" if not errors else "FAIL",
        "build_off_configuration": off.get("configuration_id", "UNSPECIFIED"),
        "build_on_configuration": on.get("configuration_id", "UNSPECIFIED"),
        "checks": checks,
        "error_count": len(errors),
        "errors": errors,
        "limitations": [
            "This report does not prove C++ compilation or header self-containment.",
            "Snapshot correctness depends on the external CMake File API collector.",
            (
                "No ROS, plugin load/unload, ABI, sanitizer, or hardware runtime "
                "test is performed."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-off", type=Path, required=True)
    parser.add_argument("--build-on", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--production-target",
        action="append",
        default=list(DEFAULT_PRODUCTION),
    )
    parser.add_argument(
        "--test-target",
        action="append",
        default=list(DEFAULT_TEST),
    )
    parser.add_argument("--plugin-target", default="staubli_driver_plugin")
    args = parser.parse_args()

    try:
        report = validate(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"validation input error: {exc}", file=sys.stderr)
        return 2

    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["execution_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
