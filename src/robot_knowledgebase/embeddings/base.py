"""Provider-neutral embedding protocol."""

from __future__ import annotations

from typing import Protocol, Sequence


class EmbeddingProvider(Protocol):
    """Implement this protocol to connect any local or hosted embedding model."""

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector for each input text."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Return a vector for a search query."""
        ...
