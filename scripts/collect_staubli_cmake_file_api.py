#!/usr/bin/env python3
"""Collect a normalized CMake File API codemodel-v2 snapshot."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def collect(
    build_dir: Path,
    build_testing: bool,
    configuration: str | None,
    exports_file: Path | None,
    export_root: Path | None = None,
) -> dict[str, Any]:
    reply = build_dir / ".cmake/api/v1/reply"
    indexes = sorted(
        reply.glob("index-*.json"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    if not indexes and (reply / "index.json").exists():
        indexes = [reply / "index.json"]
    if not indexes:
        raise FileNotFoundError(f"no CMake File API index found in {reply}")

    index = read_json(indexes[-1])
    reference = index.get("reply", {}).get("codemodel-v2")
    if not isinstance(reference, dict) or not isinstance(
        reference.get("jsonFile"), str
    ):
        raise ValueError("missing codemodel-v2 reply")

    model = read_json(reply / reference["jsonFile"])
    configurations = model.get("configurations")
    if not isinstance(configurations, list) or not configurations:
        raise ValueError("codemodel has no configurations")

    selected = next(
        (
            item
            for item in configurations
            if configuration is None or item.get("name") == configuration
        ),
        None,
    )
    if selected is None:
        raise ValueError(f"configuration {configuration!r} not found")

    references = selected.get("targets", [])
    if not isinstance(references, list):
        raise ValueError("configuration.targets must be an array")

    raw_targets = []
    target_ids = {}
    for item in references:
        if not isinstance(item, dict) or not isinstance(item.get("jsonFile"), str):
            raise ValueError("invalid target reference")
        target = read_json(reply / item["jsonFile"])
        target_id = target.get("id", item.get("id"))
        name = target.get("name", item.get("name"))
        if not isinstance(target_id, str) or not isinstance(name, str):
            raise ValueError("target requires string id and name")
        target_ids[target_id] = name
        raw_targets.append((item, target))

    targets = []
    for reference_item, target in raw_targets:
        name = target.get("name", reference_item.get("name"))
        dependencies = target.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"{name}.dependencies must be an array")
        dependency_names = sorted(
            {
                target_ids[item["id"]]
                for item in dependencies
                if isinstance(item, dict)
                and isinstance(item.get("id"), str)
                and item["id"] in target_ids
            }
        )

        includes = set()
        definitions = set()
        for group in target.get("compileGroups", []):
            if not isinstance(group, dict):
                continue
            includes.update(
                item["path"]
                for item in group.get("includes", [])
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            )
            definitions.update(
                item["define"]
                for item in group.get("defines", [])
                if isinstance(item, dict) and isinstance(item.get("define"), str)
            )

        targets.append(
            {
                "name": name,
                "type": target.get("type", reference_item.get("type", "UNKNOWN")),
                "dependencies": dependency_names,
                "include_directories": sorted(includes),
                "compile_definitions": sorted(definitions),
            }
        )

    manifest = build_dir / "install_manifest.txt"
    install_entries = (
        [
            line.strip()
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if manifest.exists()
        else []
    )

    if exports_file and export_root:
        raise ValueError(
            "use only one of --exported-targets-file and --export-root"
        )

    exported_targets = []
    exported_target_include_directories = []
    export_sources = []
    if exports_file:
        exported_targets = [
            line.strip()
            for line in exports_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        export_sources = [str(exports_file.resolve())]

    if export_root:
        prefix = export_root.resolve()
        if not prefix.is_dir():
            raise FileNotFoundError(f"export root is not a directory: {prefix}")

        pattern = re.compile(
            r"add_(?:library|executable)\s*\(\s*([A-Za-z0-9_.:+-]+)\s+"
            r"(?:(?:UNKNOWN|STATIC|SHARED|MODULE|INTERFACE)\s+)?IMPORTED\b",
            re.IGNORECASE,
        )
        cmake_dirs = [prefix / "lib" / "cmake", prefix / "share"]
        candidates = []
        for root in cmake_dirs:
            if not root.exists():
                continue
            for pattern_name in ("*Targets.cmake", "*Export.cmake"):
                candidates.extend(root.rglob(pattern_name))

        for path in sorted(set(candidates)):
            resolved = path.resolve()
            if not resolved.is_relative_to(prefix):
                continue
            relative = resolved.relative_to(prefix)
            in_lib_cmake = "lib" in relative.parts and "cmake" in relative.parts
            in_share_cmake = "share" in relative.parts and "cmake" in relative.parts
            if not (in_lib_cmake or in_share_cmake):
                continue
            content = resolved.read_text(encoding="utf-8", errors="replace")
            names = pattern.findall(content)
            if names:
                exported_targets.extend(names)
                export_sources.append(str(resolved))
            # CMake install exports encode transitive include paths in this
            # property. Preserve them so validation can detect stale absolute
            # paths such as an undefined ${asio_SOURCE_DIR} expansion.
            for value in re.findall(
                r'INTERFACE_INCLUDE_DIRECTORIES\\s+"([^"]*)"', content
            ):
                exported_target_include_directories.extend(
                    item for item in value.split(";") if item
                )

    return {
        "schema_version": "1.0.0",
        "configuration_id": str(selected.get("name") or build_dir.name),
        "build_testing": build_testing,
        "build_directory": str(build_dir.resolve()),
        "cmake_file_api_index": indexes[-1].name,
        "targets": sorted(targets, key=lambda item: item["name"]),
        "install_entries": sorted(set(install_entries)),
        "exported_targets": sorted(set(exported_targets)),
        "exported_target_include_directories": sorted(
            set(exported_target_include_directories)
        ),
        "exported_target_sources": sorted(set(export_sources)),
        "collection_scope": "cmake_file_api_codemodel_v2",
        "limitations": [
            (
                "Exported targets come from an explicit list or constrained "
                "imported-target scan under the supplied install prefix; this "
                "is not a substitute for a downstream consumer test."
            ),
            (
                "Missing install_manifest.txt yields an empty list and is not "
                "proof that install was executed."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument(
        "--build-testing", choices=("ON", "OFF"), required=True
    )
    parser.add_argument("--configuration")
    parser.add_argument("--exported-targets-file", type=Path)
    parser.add_argument("--export-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = collect(
            args.build_dir,
            args.build_testing == "ON",
            args.configuration,
            args.exported_targets_file,
            args.export_root,
        )
        encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"collector input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
