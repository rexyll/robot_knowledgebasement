import json
from pathlib import Path

import pytest

from scripts.package_staubli_build_evidence import (
    environment_fingerprint,
    package_evidence,
    verify_manifest,
)


def make_inputs(root: Path):
    files = []
    contents = (
        ("off.json", '{"build_testing":false}\n'),
        ("on.json", '{"build_testing":true}\n'),
        ("report.json", '{"execution_status":"PASS"}\n'),
    )
    for name, content in contents:
        path = root / name
        path.write_text(content, encoding="utf-8")
        files.append(path)
    return files


def test_environment_fingerprint_uses_unknown_for_missing_values(
    monkeypatch,
    tmp_path,
):
    monkeypatch.delenv("ROS_DISTRO", raising=False)
    fingerprint = environment_fingerprint(tmp_path)

    assert fingerprint["ros_distro"] == "UNKNOWN"
    assert fingerprint["environment_allowlist"]["ROS_DISTRO"] == "UNKNOWN"
    assert "git_commit" in fingerprint["source"]


def test_package_and_verify_sha256(tmp_path):
    off, on, report = make_inputs(tmp_path)
    output = tmp_path / "evidence"

    package_evidence(output, off, on, report, tmp_path)
    result = verify_manifest(output / "evidence_manifest.json")

    assert result["execution_status"] == "PASS"
    assert result["checked_artifact_count"] == 4


def test_verify_detects_tampered_artifact(tmp_path):
    off, on, report = make_inputs(tmp_path)
    output = tmp_path / "evidence"

    package_evidence(output, off, on, report)
    artifact = output / "artifacts/build-testing-off.json"
    artifact.write_text("tampered\n", encoding="utf-8")
    result = verify_manifest(output / "evidence_manifest.json")

    assert result["execution_status"] == "FAIL"
    assert any("mismatch" in error for error in result["errors"])


def test_verify_fails_when_artifact_missing(tmp_path):
    off, on, report = make_inputs(tmp_path)
    output = tmp_path / "evidence"

    package_evidence(output, off, on, report)
    (output / "artifacts/build-testing-on.json").unlink()
    result = verify_manifest(output / "evidence_manifest.json")

    assert result["execution_status"] == "FAIL"
    assert any("does not exist" in error for error in result["errors"])


def test_verify_rejects_path_traversal(tmp_path):
    manifest = tmp_path / "evidence_manifest.json"
    payload = {
        "schema_version": "1.0.0",
        "artifacts": [
            {
                "path": "../outside",
                "size_bytes": 0,
                "sha256": "0" * 64,
            }
        ],
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="escapes"):
        verify_manifest(manifest)
