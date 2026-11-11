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

def reply_file(reply: Path, filename: str, label: str) -> Path:
    """Resolve a File API filename without allowing reads outside the reply tree."""
    candidate = Path(filename)
    if candidate.is_absolute():
        raise ValueError(f"{label} must be a relative reply path: {filename!r}")
    resolved_reply = reply.resolve()
    resolved = (reply / candidate).resolve()
    if not resolved.is_relative_to(resolved_reply):
        raise ValueError(f"{label} escapes the CMake File API reply directory")
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} does not identify a reply file: {filename!r}")
    return resolved


def find_export_files(export_root: Path) -> list[Path]:
    """Find CMake exports in merged or one-package-per-prefix install layouts."""
    prefix = export_root.resolve()
    if not prefix.is_dir():
        raise FileNotFoundError(f"export root is not a directory: {prefix}")

    search_roots = [prefix / "lib" / "cmake", prefix / "share"]
    search_roots.extend(
        child / relative
        for child in prefix.iterdir()
        if child.is_dir()
        for relative in (Path("lib") / "cmake", Path("share"))
    )

    candidates = set()
    for root in search_roots:
        if not root.is_dir():
            continue
        for pattern_name in ("*Targets.cmake", "*Export.cmake"):
            candidates.update(root.rglob(pattern_name))

    export_files = []
    for path in sorted(candidates):
        resolved = path.resolve()
        if not resolved.is_relative_to(prefix):
            raise ValueError(
                f"CMake export candidate escapes install prefix: {path}"
            )
        relative = resolved.relative_to(prefix)
        in_lib_cmake = "lib" in relative.parts and "cmake" in relative.parts
        in_share_cmake = "share" in relative.parts and "cmake" in relative.parts
        if in_lib_cmake or in_share_cmake:
            export_files.append(resolved)
    return export_files


def read_export_file(path: Path) -> str:
    """Read a CMake export without silently replacing undecodable bytes."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"CMake export file is not valid UTF-8: {path}") from exc


def split_cmake_list(value: str) -> list[str]:
    """Split a CMake list while honoring escaped separators and quoted escapes."""
    items = []
    current = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            escaped = value[index + 1]
            if escaped == "\r" and index + 2 < len(value) and value[index + 2] == "\n":
                index += 3
                continue
            if escaped == "\n":
                index += 2
                continue
            if escaped == "t":
                current.append("\t")
            elif escaped == "r":
                current.append("\r")
            elif escaped == "n":
                current.append("\n")
            elif not escaped.isalnum() or escaped == "_":
                current.append(escaped)
            else:
                current.extend((char, escaped))
            index += 2
            continue
        if char == ";":
            item = "".join(current)
            if item:
                items.append(item)
            current = []
        else:
            current.append(char)
        index += 1
    item = "".join(current)
    if item:
        items.append(item)
    return items


def collect_exported_target_include_directories(export_root: Path) -> list[str]:
    """Read interface include paths from installed CMake export files."""
    include_directories = set()
    property_pattern = re.compile(
        r'INTERFACE_INCLUDE_DIRECTORIES\s+"((?:\\[\s\S]|[^"\\])*)"'
    )
    for path in find_export_files(export_root):
        content = read_export_file(path)
        for value in property_pattern.findall(content):
            include_directories.update(split_cmake_list(value))
    return sorted(include_directories)


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

    index_path = reply_file(reply, indexes[-1].name, "CMake File API index")
    index = read_json(index_path)
    replies = index.get("reply")
    if not isinstance(replies, dict):
        raise ValueError("CMake File API index.reply must be an object")
    reference = replies.get("codemodel-v2")
    if not isinstance(reference, dict) or not isinstance(
        reference.get("jsonFile"), str
    ):
        raise ValueError("missing codemodel-v2 reply")

    model_path = reply_file(reply, reference["jsonFile"], "codemodel-v2 jsonFile")
    model = read_json(model_path)
    configurations = model.get("configurations")
    if not isinstance(configurations, list) or not configurations:
        raise ValueError("codemodel has no configurations")
    configuration_names = []
    for item in configurations:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("each codemodel configuration requires a string name")
        configuration_names.append(item["name"])
    if len(configuration_names) != len(set(configuration_names)):
        raise ValueError("codemodel contains duplicate configuration names")

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
        target_path = reply_file(reply, item["jsonFile"], "target jsonFile")
        target = read_json(target_path)
        reference_id = item.get("id")
        reference_name = item.get("name")
        target_id = target.get("id")
        name = target.get("name")
        target_type = target.get("type")
        if not isinstance(reference_id, str) or not isinstance(
            reference_name, str
        ):
            raise ValueError("codemodel target reference requires string id and name")
        if not isinstance(target_id, str) or not isinstance(name, str):
            raise ValueError("target JSON requires string id and name")
        allowed_target_types = {
            "EXECUTABLE",
            "STATIC_LIBRARY",
            "SHARED_LIBRARY",
            "MODULE_LIBRARY",
            "OBJECT_LIBRARY",
            "INTERFACE_LIBRARY",
            "UNKNOWN_LIBRARY",
            "UTILITY",
        }
        if target_type not in allowed_target_types:
            raise ValueError(
                f"{name}.type must be a recognized CMake target type, "
                f"got {target_type!r}"
            )
        if target_id != reference_id:
            raise ValueError(
                f"target id mismatch for {reference_name}: "
                f"reference={reference_id!r}, target={target_id!r}"
            )
        if name != reference_name:
            raise ValueError(
                f"target name mismatch for {reference_id}: "
                f"reference={reference_name!r}, target={name!r}"
            )
        if target_id in target_ids:
            raise ValueError(f"duplicate CMake target id: {target_id}")
        target_ids[target_id] = name
        raw_targets.append((item, target))

    targets = []
    for reference_item, target in raw_targets:
        name = target.get("name", reference_item.get("name"))
        dependencies = target.get("dependencies", [])
        if not isinstance(dependencies, list):
            raise ValueError(f"{name}.dependencies must be an array")
        dependency_ids = []
        for dependency in dependencies:
            if not isinstance(dependency, dict) or not isinstance(
                dependency.get("id"), str
            ):
                raise ValueError(f"{name}.dependencies contains an invalid target reference")
            dependency_id = dependency["id"]
            if dependency_id not in target_ids:
                raise ValueError(
                    f"{name}.dependencies references unknown target id: {dependency_id}"
                )
            dependency_ids.append(dependency_id)
        dependency_names = sorted({target_ids[item] for item in dependency_ids})

        compile_groups = target.get("compileGroups", [])
        if not isinstance(compile_groups, list):
            raise ValueError(f"{name}.compileGroups must be an array")
        includes = set()
        definitions = set()
        for group in compile_groups:
            if not isinstance(group, dict):
                raise ValueError(f"{name}.compileGroups contains an invalid group")
            group_includes = group.get("includes", [])
            if not isinstance(group_includes, list):
                raise ValueError(f"{name}.compileGroups.includes must be an array")
            for include in group_includes:
                if not isinstance(include, dict) or not isinstance(
                    include.get("path"), str
                ):
                    raise ValueError(
                        f"{name}.compileGroups.includes contains an invalid entry"
                    )
                includes.add(include["path"])
            group_defines = group.get("defines", [])
            if not isinstance(group_defines, list):
                raise ValueError(f"{name}.compileGroups.defines must be an array")
            for define in group_defines:
                if not isinstance(define, dict) or not isinstance(
                    define.get("define"), str
                ):
                    raise ValueError(
                        f"{name}.compileGroups.defines contains an invalid entry"
                    )
                definitions.add(define["define"])

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
    install_entries = []
    if manifest.exists():
        install_entries = [
            line.strip()
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        relative_entries = [
            entry for entry in install_entries if not Path(entry).is_absolute()
        ]
        if relative_entries:
            raise ValueError(
                "install_manifest.txt contains non-absolute paths: "
                + ", ".join(relative_entries)
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
            r"(?m)^[ \t]*add_(?:library|executable)\s*\(\s*([A-Za-z0-9_.:+-]+)\s+"
            r"(?:(?:UNKNOWN|STATIC|SHARED|MODULE|OBJECT|INTERFACE)\s+)?IMPORTED\b",
            re.IGNORECASE,
        )
        for resolved in find_export_files(prefix):
            content = read_export_file(resolved)
            names = pattern.findall(content)
            if names:
                exported_targets.extend(names)
                export_sources.append(str(resolved))
        exported_target_include_directories = (
            collect_exported_target_include_directories(prefix)
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
