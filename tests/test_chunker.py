import pytest

from robot_knowledgebase.ingest.chunker import chunk_text


def test_chunk_text_returns_single_chunk_for_short_text():
    assert chunk_text("hello world", chunk_size=20, overlap=2) == ["hello world"]


def test_chunk_text_splits_long_text_and_preserves_content():
    text = "alpha beta gamma delta epsilon zeta eta theta"
    chunks = chunk_text(text, chunk_size=18, overlap=4)

    assert len(chunks) > 1
    assert all(chunks)
    assert all(len(chunk) <= 18 for chunk in chunks)
    assert "alpha" in chunks[0]
    assert "theta" in chunks[-1]


def test_chunk_text_handles_empty_input():
    assert chunk_text("  ") == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)],
)
def test_chunk_text_validates_parameters(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=chunk_size, overlap=overlap)
