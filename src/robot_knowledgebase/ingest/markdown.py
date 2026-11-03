"""Dependency-free Markdown loader with conservative YAML front-matter parsing."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from robot_knowledgebase.models import KnowledgeDocument

_FRONT_MATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_HEADING = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)


def _parse_scalar(value: str) -> Any:
    """Parse common flat YAML scalar forms without pretending to be a full YAML parser."""
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [_parse_scalar(item) for item in inner.split(",")] if inner else []
    try:
        return int(value)
    except ValueError:
        return value


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}, text

    metadata: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            metadata[key] = _parse_scalar(value)
    return metadata, text[match.end() :]


def load_markdown(path: str | Path) -> KnowledgeDocument:
    """Load a Markdown file and retain its path and flat front-matter metadata."""
    source_path = Path(path)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    raw_text = source_path.read_text(encoding="utf-8")
    metadata, content = _parse_front_matter(raw_text)
    heading = _HEADING.search(content)
    title = str(metadata.get("title") or (heading.group(1) if heading else source_path.stem))
    document_id = hashlib.sha256(
        f"{source_path.as_posix()}\0{raw_text}".encode()
    ).hexdigest()

    metadata.setdefault("category", "general")
    metadata["source_path"] = source_path.as_posix()

    return KnowledgeDocument(
        document_id=document_id,
        content=content.strip(),
        source=source_path.as_posix(),
        title=title,
        metadata=metadata,
    )
