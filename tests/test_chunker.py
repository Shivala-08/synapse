"""Unit tests for src/pipeline/chunker.py (token-based chunking).

Uses the SimpleWordTokenizer fallback so tests are deterministic and offline
(no Hugging Face model download).

Run: python -m pytest tests/test_chunker.py -q
"""

import pytest

import src.pipeline.chunker as chunker
from src.pipeline.chunker import SimpleWordTokenizer, chunk_text


@pytest.fixture(autouse=True)
def force_simple_tokenizer(monkeypatch):
    """Force the word-boundary tokenizer for all tests in this module."""
    monkeypatch.setattr(chunker, "_tokenizer", SimpleWordTokenizer())


def test_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_single_chunk():
    text = "word " * 50
    chunks = chunk_text(text, chunk_size=1024, chunk_overlap=200, doc_id="doc.txt")
    assert len(chunks) == 1
    assert chunks[0]["id"] == "doc.txt_chunk_0000"
    assert chunks[0]["metadata"]["doc_id"] == "doc.txt"
    assert chunks[0]["metadata"]["chunk_index"] == 0


def test_multiple_chunks_respect_size():
    text = "word " * 3000
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=100, doc_id="big.txt")
    assert len(chunks) > 1
    assert [c["metadata"]["chunk_index"] for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert len(c["text"].split()) <= 1000


def test_overlap_between_chunks():
    text = " ".join(f"w{i}" for i in range(200))
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20, doc_id="ov.txt")
    assert len(chunks) >= 2
    shared = set(chunks[0]["text"].split()) & set(chunks[1]["text"].split())
    assert len(shared) >= 15  # ~20-token overlap, with a small safety margin


def test_token_position_metadata():
    text = " ".join(f"w{i}" for i in range(300))
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20, doc_id="meta.txt")
    for c in chunks:
        assert c["metadata"]["start_char"] < c["metadata"]["end_char"]
    # Consecutive chunks advance the window forward
    assert chunks[1]["metadata"]["start_char"] > chunks[0]["metadata"]["start_char"]


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
