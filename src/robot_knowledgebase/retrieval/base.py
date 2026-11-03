"""Provider-neutral retrieval protocol."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from robot_knowledgebase.models import SearchResult


class Retriever(Protocol):
    """Implement this protocol for a vector, keyword, or hybrid search backend."""

    def search(self, query: str, top_k: int = 5) -> Sequence[SearchResult]:
        """Return the most relevant chunks for a natural-language query."""
        ...
