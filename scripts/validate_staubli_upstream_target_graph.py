#!/usr/bin/env python3
"""Validate the fixed upstream Stäubli driver target graph and install boundary."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PRODUCTION_TARGETS = (
    "staubli_robot_driver",
    "staubli_robot_driver_hardware_interface",
)
GTEST_TARGETS = (
    "test_primitives_serialization",
    "test_message_serialization",
    "test_sockets",
    "test_rt_socket_interface",
    "test_robot_driver",
    "test_mock_robot_server",
    "test_staubli_hardware_interface",
)
PLUGIN_TARGET = "staubli_robot_driver_hardware_interface"
DIAGNOSTIC_TARGET = "test_receive_robot_state"
FORBIDDEN_TOKENS = (
    "staubli_socket_test_support",
    "staubli_socket_unit_tests",
    "FakeClock",
    "DeterministicBarrier",
    "DeterministicLatch",
    "DeterministicExecutor",
    "FaultInjector",
    "FaultScript",
)


def load_snapshot(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: snapshot must be a JSON object")
    return value


def target_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = snapshot.get("targets")
    if not isinstance(items, list):
        raise ValueError("snapshot.targets must be an array")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("each target must have a string name")
        name = item["name"]
        if name in result:
            raise ValueError(f"duplicate target: {name}")
        dependencies = item.get("dependencies", [])
        if not isinstance(dependencies, list) or any(
            not isinstance(value, str) for value in dependencies
        ):
            raise ValueError(f"{name}.dependencies must be an array of strings")
        result[name] = item
    return result


def transitive_closure(
    targets: dict[str, dict[str, Any]], roots: tuple[str, ...]
) -> set[str]:
    seen: set[str] = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        target = targets.get(name)
        if target is not None:
            pending.extend(target.get("dependencies", []))
    return seen


def normalized_exports(values: list[str]) -> set[str]:
    return {value.rsplit("::", 1)[-1] for value in values}


def validate(args: argparse.Namespace) -> dict[str, Any]:
    off = load_snapshot(args.build_off)
    on = load_snapshot(args.build_on)
    off_targets = target_map(off)
    on_targets = target_map(on)
    checks: list[dict[str, str]] = []
    errors: list[str] = []

    def check(check_id: str, passed: bool, detail: str) -> None:
        checks.append(
            {"id": check_id, "status": "PASS" if passed else "FAIL", "detail": detail}
        )
        if not passed:
            errors.append(f"{check_id}: {detail}")

    check(
        "CONFIG-BUILD-TESTING-OFF",
        off.get("build_testing") is False,
        "OFF snapshot must record build_testing=false",
    )
    check(
        "CONFIG-BUILD-TESTING-ON",
        on.get("build_testing") is True,
        "ON snapshot must record build_testing=true",
    )

    for name in PRODUCTION_TARGETS:
        check(
            f"PRODUCTION-OFF-{name}",
            name in off_targets,
            f"{name} must exist when BUILD_TESTING=OFF",
        )
        check(
            f"PRODUCTION-ON-{name}",
            name in on_targets,
            f"{name} must exist when BUILD_TESTING=ON",
        )

    for label, targets in (("OFF", off_targets), ("ON", on_targets)):
        for name in PRODUCTION_TARGETS:
            target = targets.get(name)
            check(
                f"PRODUCTION-TYPE-{label}-{name}",
                target is not None and target.get("type") == "SHARED_LIBRARY",
                f"{name} must be a SHARED_LIBRARY in BUILD_TESTING={label}",
            )

    for name in GTEST_TARGETS:
        check(
            f"GTEST-ABSENT-OFF-{name}",
            name not in off_targets,
            f"{name} must not exist when BUILD_TESTING=OFF",
        )
        check(
            f"GTEST-PRESENT-ON-{name}",
            name in on_targets,
            f"{name} must exist when BUILD_TESTING=ON",
        )

    for name in GTEST_TARGETS:
        target = on_targets.get(name)
        check(
            f"GTEST-TYPE-ON-{name}",
            target is not None and target.get("type") == "EXECUTABLE",
            f"{name} must be an EXECUTABLE when BUILD_TESTING=ON",
        )

    for label, targets in (("OFF", off_targets), ("ON", on_targets)):
        check(
            f"DIAGNOSTIC-TARGET-{label}",
            DIAGNOSTIC_TARGET in targets,
            f"{DIAGNOSTIC_TARGET} is an always-defined diagnostic executable, not a gtest target",
        )
        diagnostic = targets.get(DIAGNOSTIC_TARGET)
        check(
            f"DIAGNOSTIC-TYPE-{label}",
            diagnostic is not None and diagnostic.get("type") == "EXECUTABLE",
            f"{DIAGNOSTIC_TARGET} must remain an EXECUTABLE in BUILD_TESTING={label}",
        )

    production_closure = transitive_closure(on_targets, PRODUCTION_TARGETS)
    leaked_dependencies = sorted(
        name
        for name in production_closure
        if name in GTEST_TARGETS
        or any(token.casefold() in name.casefold() for token in FORBIDDEN_TOKENS)
    )
    check(
        "PRODUCTION-CLOSURE-EXCLUDES-TESTS",
        not leaked_dependencies,
        "production dependency closure must exclude gtest/fake targets: "
        + (", ".join(leaked_dependencies) or "none"),
    )

    plugin = on_targets.get(PLUGIN_TARGET)
    plugin_closure = transitive_closure(on_targets, (PLUGIN_TARGET,))
    plugin_leaks = sorted(
        name
        for name in plugin_closure
        if name in GTEST_TARGETS
        or any(token.casefold() in name.casefold() for token in FORBIDDEN_TOKENS)
    )
    check(
        "PLUGIN-CLOSURE-EXCLUDES-TESTS",
        plugin is not None and not plugin_leaks,
        "hardware-interface plugin closure must exclude gtest/fake targets: "
        + (", ".join(plugin_leaks) or "none"),
    )

    for label, snapshot in (("OFF", off), ("ON", on)):
        install_entries = snapshot.get("install_entries", [])
        if not isinstance(install_entries, list) or any(
            not isinstance(value, str) for value in install_entries
        ):
            raise ValueError(f"{label}.install_entries must be an array of strings")
        leaked_install = sorted(
            name
            for name in GTEST_TARGETS
            if any(Path(entry).name == name for entry in install_entries)
        )
        check(
            f"INSTALL-EXCLUDES-GTEST-{label}",
            not leaked_install,
            "install manifest must not contain gtest executables: "
            + (", ".join(leaked_install) or "none"),
        )
        check(
            f"DIAGNOSTIC-INSTALLED-{label}",
            any(DIAGNOSTIC_TARGET in entry for entry in install_entries),
            f"install manifest must retain the explicitly installed {DIAGNOSTIC_TARGET} utility",
        )

        exports = snapshot.get("exported_targets", [])
        if not isinstance(exports, list) or any(
            not isinstance(value, str) for value in exports
        ):
            raise ValueError(f"{label}.exported_targets must be an array of strings")
        export_names = normalized_exports(exports)
        missing_exports = sorted(set(PRODUCTION_TARGETS) - export_names)
        if "exported_target_include_directories" not in snapshot:
            raise ValueError(
                f"{label}.exported_target_include_directories is required; "
                "recollect the install export snapshot"
            )
        exported_includes = snapshot["exported_target_include_directories"]
        if not isinstance(exported_includes, list) or any(
            not isinstance(value, str) for value in exported_includes
        ):
            raise ValueError(
                f"{label}.exported_target_include_directories must be an array of strings"
            )
        unresolved_asio_paths = sorted(
            value
            for value in exported_includes
            if value == "/asio/include"
            or "${asio_SOURCE_DIR}" in value
        )
        check(
            f"EXPORT-EXCLUDES-UNRESOLVED-ASIO-INCLUDE-{label}",
            not unresolved_asio_paths,
            "exported target include directories must not contain the unresolved "
            "standalone Asio path: "
            + (", ".join(unresolved_asio_paths) or "none"),
        )
        leaked_exports = sorted(name for name in GTEST_TARGETS if name in export_names)
        check(
            f"EXPORT-PRODUCTION-TARGETS-{label}",
            not missing_exports,
            "export set must include both production libraries: "
            + (", ".join(missing_exports) or "complete"),
        )
        check(
            f"EXPORT-EXCLUDES-GTEST-{label}",
            not leaked_exports,
            "export set must exclude gtest executables: "
            + (", ".join(leaked_exports) or "none"),
        )

    return {
        "schema_version": "1.0.0",
        "validator": "validate_staubli_upstream_target_graph",
        "validation_scope": "fixed_upstream_cmake_target_graph_install_manifest_and_ament_exports",
        "execution_status": "PASS" if not errors else "FAIL",
        "build_off_configuration": off.get("configuration_id", "UNSPECIFIED"),
        "build_on_configuration": on.get("configuration_id", "UNSPECIFIED"),
        "production_target_count": len(PRODUCTION_TARGETS),
        "gtest_target_count": len(GTEST_TARGETS),
        "check_count": len(checks),
        "error_count": len(errors),
        "checks": checks,
        "errors": errors,
        "limitations": [
            "A normalized CMake File API snapshot does not prove C++ runtime behavior.",
            (
                "Install manifest and imported target scanning do not replace an "
                "install-space consumer build."
            ),
            (
                "Plugin load/unload, ABI, sanitizer, ROS runtime, VAL3, CS9, HIL "
                "and real-robot tests are outside this validator."
            ),
            (
                "The diagnostic executable test_receive_robot_state is "
                "intentionally installed by the fixed upstream CMakeLists.txt "
                "and is not classified as an ament gtest target."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-off", type=Path, required=True)
    parser.add_argument("--build-on", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        report = validate(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"upstream target graph validation error: {exc}", file=sys.stderr)
        return 2

    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["execution_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
