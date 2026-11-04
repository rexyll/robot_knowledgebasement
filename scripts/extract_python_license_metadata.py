#!/usr/bin/env python3
"""Extract license metadata candidates from the four Python CycloneDX BOMs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

BOMS = {
    "robot-knowledgebase-runtime.cdx.json": "python-runtime",
    "robot-knowledgebase-development.cdx.json": "python-development",
    "robot-knowledgebase-generator.cdx.json": "sbom-generator-toolchain",
    "robot-knowledgebase-build-tools.cdx.json": "pep517-build-toolchain",
}
FIELDS = [
    "scope",
    "component_type",
    "group",
    "name",
    "version",
    "purl",
    "bom_ref",
    "license_values",
    "metadata_forms",
    "acknowledgements",
    "license_metadata_json",
    "source_bom",
    "review_status",
    "notes",
]


def extract_license_metadata(
    component: dict[str, Any],
) -> tuple[list[str], list[str], list[str], str]:
    raw = component.get("licenses") or []
    values: list[str] = []
    forms: list[str] = []
    acknowledgements: list[str] = []
    for entry in raw:
        license_data = entry.get("license", entry)
        if "expression" in license_data:
            form, value = "SPDX-expression-candidate", license_data["expression"]
        elif "id" in license_data:
            form, value = "SPDX-ID-candidate", license_data["id"]
        elif "name" in license_data:
            form, value = "free-text-or-classifier", license_data["name"]
        else:
            form, value = "unclassified-metadata", json.dumps(
                license_data, ensure_ascii=False, sort_keys=True
            )
        values.append(str(value))
        forms.append(form)
        acknowledgement = entry.get("acknowledgement")
        if acknowledgement:
            acknowledgements.append(str(acknowledgement))
    if not raw:
        forms.append("missing")
    raw_json = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return values, sorted(set(forms)), sorted(set(acknowledgements)), raw_json


def build_rows(sbom_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for filename, scope in BOMS.items():
        path = sbom_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Required CycloneDX BOM is missing: {path}")
        bom = json.loads(path.read_text(encoding="utf-8"))
        if bom.get("specVersion") != "1.7":
            raise ValueError(f"Expected CycloneDX 1.7 in {filename}")
        components = bom.get("components")
        if not isinstance(components, list) or not components:
            raise ValueError(f"No components found in {filename}")
        for component in components:
            values, forms, acknowledgements, raw_json = extract_license_metadata(component)
            rows.append(
                {
                    "scope": scope,
                    "component_type": str(component.get("type", "")),
                    "group": str(component.get("group", "")),
                    "name": str(component.get("name", "")),
                    "version": str(component.get("version", "")),
                    "purl": str(component.get("purl", "")),
                    "bom_ref": str(component.get("bom-ref", "")),
                    "license_values": " | ".join(values),
                    "metadata_forms": " | ".join(forms),
                    "acknowledgements": " | ".join(acknowledgements),
                    "license_metadata_json": raw_json,
                    "source_bom": filename,
                    "review_status": "pending_manual_review",
                    "notes": (
                        "CycloneDX package metadata is a review candidate only; "
                        "not a legal conclusion or redistribution approval."
                    ),
                }
            )
    rows.sort(key=lambda row: (row["scope"], row["name"].casefold(), row["version"]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sbom-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = build_rows(args.sbom_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Extracted {len(rows)} license metadata candidates from {len(BOMS)} CycloneDX BOMs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
