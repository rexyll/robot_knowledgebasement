#!/usr/bin/env python3
"""Capture a Stäubli build environment and package hash-verifiable evidence."""
from __future__ import annotations  # noqa: I001

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENV_ALLOWLIST = (
    "ROS_DISTRO",
    "CC",
    "CXX",
    "CMAKE_GENERATOR",
    "CMAKE_TOOLCHAIN_FILE",
    "CMAKE_BUILD_TYPE",
    "BUILD_TESTING",
    "CMAKE_PREFIX_PATH",
    "AMENT_PREFIX_PATH",
    "COLCON_PREFIX_PATH",
    "PKG_CONFIG_PATH",
)


def command_version(argv: list[str]) -> str:
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN"
    lines = (result.stdout + "\n" + result.stderr).strip().splitlines()
    return lines[0].strip()[:500] if lines else "UNKNOWN"


def git_value(source: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source), *args],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN"
    value = result.stdout.strip()
    if result.returncode == 0 and value:
        return value
    return "UNKNOWN"


def environment_fingerprint(source_dir: Path | None = None) -> dict[str, Any]:
    source = source_dir.resolve() if source_dir else None
    compiler = os.environ.get("CXX") or "c++"
    return {
        "schema_version": "1.0.0",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform() or "UNKNOWN",
        "architecture": platform.machine() or "UNKNOWN",
        "python": sys.version.split()[0] if sys.version else "UNKNOWN",
        "cmake": command_version(["cmake", "--version"]),
        "compiler": command_version([compiler, "--version"]),
        "colcon": command_version(["colcon", "--version"]),
        "ros_distro": os.environ.get("ROS_DISTRO", "UNKNOWN"),
        "environment_allowlist": {
            key: os.environ.get(key, "UNKNOWN") for key in ENV_ALLOWLIST
        },
        "source": {
            "path": str(source) if source else "UNKNOWN",
            "git_commit": (
                git_value(source, "rev-parse", "HEAD") if source else "UNKNOWN"
            ),
            "git_dirty": (
                git_value(source, "status", "--porcelain")
                if source
                else "UNKNOWN"
            ),
        },
        "unknown_policy": (
            "Unavailable values are literal UNKNOWN; no version is inferred "
            "or fabricated."
        ),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_artifact(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"required evidence artifact missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def package_evidence(
    output_dir: Path,
    build_off: Path,
    build_on: Path,
    validator_report: Path,
    source_dir: Path | None = None,
    command_log: Path | None = None,
) -> dict[str, Any]:
    output = output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    artifact_dir = output / "artifacts"
    inputs = [
        (build_off, artifact_dir / "build-testing-off.json"),
        (build_on, artifact_dir / "build-testing-on.json"),
        (validator_report, artifact_dir / "servo-901-validation-report.json"),
    ]
    if command_log:
        inputs.append((command_log, artifact_dir / "commands.log"))

    copied = [copy_artifact(source.resolve(), destination) for source, destination in inputs]
    fingerprint = output / "environment-fingerprint.json"
    fingerprint.write_text(
        json.dumps(
            environment_fingerprint(source_dir),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    copied.append(fingerprint)

    records = [
        {
            "path": path.relative_to(output).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in copied
    ]
    manifest = {
        "schema_version": "1.0.0",
        "evidence_package": "staubli-build-testing-matrix",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": [sys.executable, str(Path(__file__).resolve()), "package"],
        "artifacts": records,
        "integrity": "sha256",
        "verification_policy": (
            "Every listed artifact must exist under this package root and "
            "match its recorded size and SHA-256."
        ),
    }
    (output / "evidence_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1.0.0":
        raise ValueError("unsupported or malformed evidence manifest")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError(
            "evidence manifest must contain a non-empty artifacts array"
        )

    checks = []
    errors = []
    for item in artifacts:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("each artifact requires a relative path")
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"artifact path escapes evidence root: {relative}")
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"artifact path escapes evidence root: {relative}")

        if not path.is_file():
            status, detail = "MISSING", "artifact file does not exist"
        elif path.stat().st_size != item.get("size_bytes"):
            status, detail = "FAIL", "size mismatch"
        elif sha256(path) != item.get("sha256"):
            status, detail = "FAIL", "sha256 mismatch"
        else:
            status, detail = "PASS", "size and sha256 match"

        checks.append(
            {"path": item["path"], "status": status, "detail": detail}
        )
        if status != "PASS":
            errors.append(item["path"] + ": " + detail)

    return {
        "execution_status": "PASS" if not errors else "FAIL",
        "checked_artifact_count": len(checks),
        "checks": checks,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    fingerprint_parser = subparsers.add_parser("fingerprint")
    fingerprint_parser.add_argument("--source-dir", type=Path)
    fingerprint_parser.add_argument("--output", type=Path, required=True)

    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("--output-dir", type=Path, required=True)
    package_parser.add_argument("--build-off", type=Path, required=True)
    package_parser.add_argument("--build-on", type=Path, required=True)
    package_parser.add_argument("--validator-report", type=Path, required=True)
    package_parser.add_argument("--source-dir", type=Path)
    package_parser.add_argument("--command-log", type=Path)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.action == "fingerprint":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(
                    environment_fingerprint(args.source_dir),
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            result = {
                "execution_status": "CAPTURED",
                "output": str(args.output),
            }
        elif args.action == "package":
            manifest = package_evidence(
                args.output_dir,
                args.build_off,
                args.build_on,
                args.validator_report,
                args.source_dir,
                args.command_log,
            )
            result = {
                "execution_status": "PACKAGED",
                "manifest": str(args.output_dir / "evidence_manifest.json"),
                "artifact_count": len(manifest["artifacts"]),
            }
        else:
            result = verify_manifest(args.manifest)

        print(json.dumps(result, indent=2, ensure_ascii=False))
        successful = ("CAPTURED", "PACKAGED", "PASS")
        return 0 if result.get("execution_status") in successful else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"evidence error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
