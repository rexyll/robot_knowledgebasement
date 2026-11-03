"""Shared data models used across ingestion and retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KnowledgeDocument:
    """A source document and its provenance metadata."""

    document_id: str
    content: str
    source: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentChunk:
    """A deterministic text segment derived from a knowledge document."""

    document_id: str
    chunk_index: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SearchResult:
    """A retrieved chunk with an optional relevance score."""

    chunk: DocumentChunk
    score: float | None = None
