"""Simple deterministic character-based text chunking."""

from __future__ import annotations

from robot_knowledgebase.models import DocumentChunk, KnowledgeDocument


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks, preferring whitespace boundaries."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if overlap < 0:
        raise ValueError("overlap cannot be negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized = text.strip()
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length:
            boundary = normalized.rfind(" ", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary

        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= text_length:
            break
        start = max(start + 1, end - overlap)

    return chunks


def chunk_document(
    document: KnowledgeDocument, chunk_size: int = 1000, overlap: int = 150
) -> list[DocumentChunk]:
    """Chunk a document while copying provenance metadata to every chunk."""
    return [
        DocumentChunk(
            document_id=document.document_id,
            chunk_index=index,
            text=piece,
            metadata={**document.metadata, "title": document.title, "source": document.source},
        )
        for index, piece in enumerate(chunk_text(document.content, chunk_size, overlap))
    ]
