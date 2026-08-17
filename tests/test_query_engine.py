"""Unit tests for src/pipeline/query_engine.py (pure logic + fallback path).

Heavy network-dependent pieces (HF embeddings, ChromaDB, cross-encoder, live
LLM) are not exercised here; those are covered by tests/test_chromadb.py and
the benchmark harness (run_benchmark_now.py) instead.

Run: python -m pytest tests/test_query_engine.py -q
"""

import numpy as np
import pytest

from src.pipeline import query_engine


# ── classify_query_complexity ─────────────────────────────────────────────────

def test_classify_simple_query_is_fast():
    res = query_engine.classify_query_complexity(
        "What is the inspection frequency for pumps?", []
    )
    assert res["is_complex"] is False
    assert res["enable_thinking"] is False
    assert res["reasoning_budget"] == 0


def test_classify_long_query_is_complex():
    res = query_engine.classify_query_complexity("x" * 200, [])
    assert res["is_complex"] is True
    assert res["enable_thinking"] is True
    assert res["reasoning_budget"] == 1024


@pytest.mark.parametrize("q", [
    "Compare hot work and cold work requirements",
    "What is the difference between OISD-116 and OISD-117?",
    "List all PPE requirements for mining workers",
    "Which permits are required and which are optional?",
])
def test_classify_comparison_queries_are_complex(q):
    res = query_engine.classify_query_complexity(q, [])
    assert res["is_complex"] is True


def test_classify_multi_doc_close_chunks_is_complex():
    chunks = [
        {"metadata": {"doc_id": "a"}, "distance": 0.30},
        {"metadata": {"doc_id": "b"}, "distance": 0.35},
    ]
    res = query_engine.classify_query_complexity("A question about safety procedures", chunks)
    assert res["is_complex"] is True


def test_classify_same_doc_chunks_is_simple():
    chunks = [
        {"metadata": {"doc_id": "a"}, "distance": 0.30},
        {"metadata": {"doc_id": "a"}, "distance": 0.35},
    ]
    res = query_engine.classify_query_complexity("A question about safety procedures", chunks)
    assert res["is_complex"] is False


def test_classify_distant_chunks_is_simple():
    chunks = [
        {"metadata": {"doc_id": "a"}, "distance": 0.10},
        {"metadata": {"doc_id": "b"}, "distance": 0.60},
    ]
    res = query_engine.classify_query_complexity("A question about safety procedures", chunks)
    assert res["is_complex"] is False


# ── SemanticCache ─────────────────────────────────────────────────────────────

def _vec(*vals):
    return np.array(vals, dtype=float)


def test_semantic_cache_hit(tmp_path, monkeypatch):
    monkeypatch.setattr(query_engine.settings, "data_dir", tmp_path)
    cache = query_engine.SemanticCache(max_size=10, threshold=0.95)
    cache.set(_vec(1.0, 0.0, 0.0), {"answer": "hello", "sources": []})
    got = cache.get(_vec(1.0, 0.0, 0.0))
    assert got is not None
    assert got["answer"] == "hello"


def test_semantic_cache_miss(tmp_path, monkeypatch):
    monkeypatch.setattr(query_engine.settings, "data_dir", tmp_path)
    cache = query_engine.SemanticCache(max_size=10, threshold=0.95)
    cache.set(_vec(1.0, 0.0, 0.0), {"answer": "hello"})
    assert cache.get(_vec(0.0, 1.0, 0.0)) is None


def test_semantic_cache_evicts_oldest(tmp_path, monkeypatch):
    monkeypatch.setattr(query_engine.settings, "data_dir", tmp_path)
    cache = query_engine.SemanticCache(max_size=3, threshold=0.95)
    for i in range(4):
        cache.set(_vec(float(i), 1.0, 0.0), {"answer": str(i)})
    assert len(cache.cache) == 3
    assert cache.cache[0]["answer"]["answer"] == "1"  # first entry evicted (FIFO)


def test_semantic_cache_persists_to_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(query_engine.settings, "data_dir", tmp_path)
    cache = query_engine.SemanticCache(max_size=10, threshold=0.95)
    emb = _vec(1.0, 0.0, 0.0)
    cache.set(emb, {"answer": "persisted"})

    cache2 = query_engine.SemanticCache(max_size=10, threshold=0.95)
    got = cache2.get(emb)
    assert got is not None
    assert got["answer"] == "persisted"


# ── generate_answer: smart-fallback path (no LLM, no network) ────────────────

class FakeEmbedder:
    def embed_query(self, query):
        return [0.1, 0.2, 0.3]


class FakeLLM:
    available = False
    model = None


class DummyCache:
    def get(self, embedding):
        return None

    def set(self, embedding, answer):
        pass


def _sample_context():
    return {
        "vector_chunks": [
            {"chunk_id": "c1",
             "text": "Hot work permits are mandatory in hazardous areas.",
             "metadata": {"doc_id": "OISD-116.txt"}, "distance": 0.40},
            {"chunk_id": "c2",
             "text": "PPE must be worn by all workers.",
             "metadata": {"doc_id": "safety_manual.txt"}, "distance": 0.60},
        ],
        "graph_entities": [{"id": "EQ-1001", "type": "equipment"}],
        "graph_relations": [{"source": "EQ-1001", "target": "OISD-116", "relation": "subject_to"}],
    }


def test_generate_answer_smart_fallback(monkeypatch):
    monkeypatch.setattr(query_engine, "get_embedder", lambda: FakeEmbedder())
    monkeypatch.setattr(query_engine, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(query_engine, "_semantic_cache", DummyCache())

    res = query_engine.generate_answer("When is a hot work permit required?", _sample_context())

    assert res["model_used"] == "Smart Context"
    assert res["confidence"] == 0.5
    assert res["entities_used"] == ["EQ-1001"]
    assert len(res["sources"]) == 2
    assert res["sources"][0]["doc_id"] == "OISD-116.txt"
    assert "Hot work permits" in res["answer"]
    assert "EQ-1001" in res["answer"]  # graph context included in fallback


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
