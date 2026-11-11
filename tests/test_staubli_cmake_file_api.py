import json
from pathlib import Path

from scripts.collect_staubli_cmake_file_api import collect


def put(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def fixture(tmp_path):
    build = tmp_path / "build"
    reply = build / ".cmake/api/v1/reply"
    put(
        reply / "index-001.json",
        {"reply": {"codemodel-v2": {"jsonFile": "codemodel-v2.json"}}},
    )
    put(
        reply / "codemodel-v2.json",
        {
            "configurations": [
                {
                    "name": "Debug",
                    "targets": [
                        {
                            "id": "core-id",
                            "name": "staubli_socket_core",
                            "jsonFile": "core.json",
                        },
                        {
                            "id": "plugin-id",
                            "name": "staubli_driver_plugin",
                            "jsonFile": "plugin.json",
                        },
                    ],
                }
            ]
        },
    )
    put(
        reply / "core.json",
        {
            "id": "core-id",
            "name": "staubli_socket_core",
            "type": "SHARED_LIBRARY",
            "dependencies": [],
            "compileGroups": [
                {
                    "includes": [{"path": "/opt/ros/include"}],
                    "defines": [{"define": "CORE_BUILD=1"}],
                }
            ],
        },
    )
    put(
        reply / "plugin.json",
        {
            "id": "plugin-id",
            "name": "staubli_driver_plugin",
            "type": "MODULE_LIBRARY",
            "dependencies": [{"id": "core-id"}],
            "compileGroups": [],
        },
    )
    (build / "install_manifest.txt").write_text(
        "/tmp/install/lib/libstaubli.so\n"
    )
    return build


def test_codemodel_targets_dependencies_and_compile_metadata(tmp_path):
    result = collect(fixture(tmp_path), False, "Debug", None)

    assert result["build_testing"] is False
    targets = {item["name"]: item for item in result["targets"]}
    assert targets["staubli_driver_plugin"]["dependencies"] == [
        "staubli_socket_core"
    ]
    assert targets["staubli_socket_core"]["include_directories"] == [
        "/opt/ros/include"
    ]
    assert targets["staubli_socket_core"]["compile_definitions"] == [
        "CORE_BUILD=1"
    ]
    assert result["install_entries"] == ["/tmp/install/lib/libstaubli.so"]


def test_exported_targets_are_explicit_input(tmp_path):
    export = tmp_path / "exports.txt"
    export.write_text("staubli_socket_core\nstaubli_driver_plugin\n")
    result = collect(fixture(tmp_path), True, "Debug", export)

    assert result["exported_targets"] == [
        "staubli_driver_plugin",
        "staubli_socket_core",
    ]


def test_missing_file_api_index_fails_closed(tmp_path):
    try:
        collect(tmp_path / "empty", False, None, None)
    except FileNotFoundError as exc:
        assert "no CMake File API index" in str(exc)
    else:
        raise AssertionError("missing index must fail")


def test_missing_configuration_fails_closed(tmp_path):
    try:
        collect(fixture(tmp_path), False, "Release", None)
    except ValueError as exc:
        assert "configuration 'Release' not found" in str(exc)
    else:
        raise AssertionError("missing configuration must fail")


def test_export_root_scans_only_imported_targets_under_cmake_exports(tmp_path):
    build = fixture(tmp_path)
    prefix = tmp_path / "prefix"
    targets = prefix / "lib/cmake/staubli/staubliTargets.cmake"
    targets.parent.mkdir(parents=True)
    targets.write_text(
        "add_library(staubli::core SHARED IMPORTED)\n"
        "add_executable(staubli::tool IMPORTED)\n",
        encoding="utf-8",
    )
    unrelated = prefix / "share/docs/Targets.cmake"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text(
        "add_library(not_exported SHARED IMPORTED)\n",
        encoding="utf-8",
    )

    result = collect(build, True, "Debug", None, prefix)

    assert result["exported_targets"] == ["staubli::core", "staubli::tool"]
    assert len(result["exported_target_sources"]) == 1


def test_export_file_and_root_are_mutually_exclusive(tmp_path):
    build = fixture(tmp_path)
    exports = tmp_path / "exports.txt"
    exports.write_text("staubli::core\n", encoding="utf-8")

    try:
        collect(build, True, "Debug", exports, tmp_path)
    except ValueError as exc:
        assert "use only one" in str(exc)
    else:
        raise AssertionError("ambiguous export inputs must fail")


def test_export_root_scans_ament_export_targets_file(tmp_path):
    build = fixture(tmp_path)
    prefix = tmp_path / "ament-prefix"
    export = (
        prefix
        / "share/staubli_robot_driver/cmake/"
        / "export_staubli_robot_driverExport.cmake"
    )
    export.parent.mkdir(parents=True)
    export.write_text(
        "add_library(staubli_robot_driver::staubli_robot_driver SHARED IMPORTED)\n"
        "set_target_properties(staubli_robot_driver::staubli_robot_driver PROPERTIES "
        "INTERFACE_INCLUDE_DIRECTORIES \"$<INSTALL_INTERFACE:include>;"
        "$<INSTALL_INTERFACE:include/staubli>\")\n"
        "add_library(staubli_robot_driver::staubli_robot_driver_hardware_interface "
        "SHARED IMPORTED)\n",
        encoding="utf-8",
    )
    result = collect(build, True, "Debug", None, prefix)

    assert result["exported_targets"] == [
        "staubli_robot_driver::staubli_robot_driver",
        "staubli_robot_driver::staubli_robot_driver_hardware_interface",
    ]
    assert result["exported_target_sources"] == [str(export.resolve())]
    assert result["exported_target_include_directories"] == [
        "$<INSTALL_INTERFACE:include/staubli>",
        "$<INSTALL_INTERFACE:include>",
    ]



def test_unknown_dependency_target_id_fails_closed(tmp_path):
    build = fixture(tmp_path)
    reply = build / ".cmake/api/v1/reply"
    plugin = json.loads((reply / "plugin.json").read_text(encoding="utf-8"))
    plugin["dependencies"] = [{"id": "missing-target-id"}]
    put(reply / "plugin.json", plugin)

    try:
        collect(build, False, "Debug", None)
    except ValueError as exc:
        assert "references unknown target id" in str(exc)
    else:
        raise AssertionError("unknown dependency target IDs must fail")


def test_malformed_dependency_reference_fails_closed(tmp_path):
    build = fixture(tmp_path)
    reply = build / ".cmake/api/v1/reply"
    plugin = json.loads((reply / "plugin.json").read_text(encoding="utf-8"))
    plugin["dependencies"] = [{"name": "staubli_socket_core"}]
    put(reply / "plugin.json", plugin)

    try:
        collect(build, False, "Debug", None)
    except ValueError as exc:
        assert "invalid target reference" in str(exc)
    else:
        raise AssertionError("malformed dependency references must fail")


def test_duplicate_cmake_target_ids_fail_closed(tmp_path):
    build = fixture(tmp_path)
    reply = build / ".cmake/api/v1/reply"
    plugin = json.loads((reply / "plugin.json").read_text(encoding="utf-8"))
    plugin["id"] = "core-id"
    put(reply / "plugin.json", plugin)
    model = json.loads((reply / "codemodel-v2.json").read_text(encoding="utf-8"))
    model["configurations"][0]["targets"][1]["id"] = "core-id"
    put(reply / "codemodel-v2.json", model)

    try:
        collect(build, False, "Debug", None)
    except ValueError as exc:
        assert "duplicate CMake target id" in str(exc)
    else:
        raise AssertionError("duplicate target IDs must fail")

def test_target_json_id_must_match_codemodel_reference(tmp_path):
    build = fixture(tmp_path)
    reply = build / ".cmake/api/v1/reply"
    core = json.loads((reply / "core.json").read_text(encoding="utf-8"))
    core["id"] = "different-core-id"
    put(reply / "core.json", core)

    try:
        collect(build, False, "Debug", None)
    except ValueError as exc:
        assert "target id mismatch" in str(exc)
    else:
        raise AssertionError("target JSON ID mismatch must fail")


def test_target_json_name_must_match_codemodel_reference(tmp_path):
    build = fixture(tmp_path)
    reply = build / ".cmake/api/v1/reply"
    core = json.loads((reply / "core.json").read_text(encoding="utf-8"))
    core["name"] = "different_core_name"
    put(reply / "core.json", core)

    try:
        collect(build, False, "Debug", None)
    except ValueError as exc:
        assert "target name mismatch" in str(exc)
    else:
        raise AssertionError("target JSON name mismatch must fail")


def test_malformed_compile_groups_fail_closed(tmp_path):
    build = fixture(tmp_path)
    reply = build / ".cmake/api/v1/reply"
    core = json.loads((reply / "core.json").read_text(encoding="utf-8"))
    core["compileGroups"] = {"includes": []}
    put(reply / "core.json", core)

    try:
        collect(build, False, "Debug", None)
    except ValueError as exc:
        assert "compileGroups must be an array" in str(exc)
    else:
        raise AssertionError("malformed compileGroups must fail")


def test_malformed_compile_include_fails_closed(tmp_path):
    build = fixture(tmp_path)
    reply = build / ".cmake/api/v1/reply"
    core = json.loads((reply / "core.json").read_text(encoding="utf-8"))
    core["compileGroups"][0]["includes"] = [{"not_path": "/opt/ros/include"}]
    put(reply / "core.json", core)

    try:
        collect(build, False, "Debug", None)
    except ValueError as exc:
        assert "includes contains an invalid entry" in str(exc)
    else:
        raise AssertionError("malformed compile include must fail")


def test_malformed_compile_definition_fails_closed(tmp_path):
    build = fixture(tmp_path)
    reply = build / ".cmake/api/v1/reply"
    core = json.loads((reply / "core.json").read_text(encoding="utf-8"))
    core["compileGroups"][0]["defines"] = [{"not_define": "CORE_BUILD=1"}]
    put(reply / "core.json", core)

    try:
        collect(build, False, "Debug", None)
    except ValueError as exc:
        assert "defines contains an invalid entry" in str(exc)
    else:
        raise AssertionError("malformed compile definition must fail")

