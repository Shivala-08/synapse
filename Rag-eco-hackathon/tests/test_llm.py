"""Unit tests for src/pipeline/llm.py (JSON parsing, smart fallback, NIM config).

Only pure/offline helpers are tested here — no network calls to NVIDIA/Ollama.

Run: python -m pytest tests/test_llm.py -q
"""

import pytest

from src.pipeline.llm import NvidiaLLM, _extract_json, _smart_fallback


# ── _extract_json ─────────────────────────────────────────────────────────────

def test_extract_json_direct():
    assert _extract_json('{"answer": "hi"}') == {"answer": "hi"}


def test_extract_json_markdown_fence():
    assert _extract_json('```json\n{"answer": "hi"}\n```') == {"answer": "hi"}


def test_extract_json_think_block():
    raw = '<think>let me reason carefully</think>{"answer": "hi"}'
    assert _extract_json(raw) == {"answer": "hi"}


def test_extract_json_embedded_in_text():
    assert _extract_json('Some preamble {"answer": "hi"} trailing') == {"answer": "hi"}


def test_extract_json_invalid_raises():
    with pytest.raises(ValueError):
        _extract_json("this is not json at all")


# ── _smart_fallback ───────────────────────────────────────────────────────────

def test_smart_fallback_no_chunks():
    res = _smart_fallback("some question", [], [])
    assert res["confidence"] == "Low"
    assert "No relevant documents" in res["answer"]


def test_smart_fallback_with_chunks():
    chunks = [{
        "doc_id": "OISD-116.txt",
        "text": "Hot work permits are mandatory in hazardous areas.",
        "citation": "OISD-116.txt",
        "distance": 0.4,
    }]
    res = _smart_fallback("When is a hot work permit required?", chunks, [])
    assert "OISD-116.txt" in res["answer"]
    assert "Hot work permits" in res["answer"]
    assert res["confidence"] == "Medium"
    assert res["key_points"]


def test_smart_fallback_with_graph_context():
    chunks = [{"doc_id": "d.txt", "text": "PPE must be worn.", "citation": "d.txt", "distance": 0.5}]
    res = _smart_fallback("What PPE is required?", chunks, ["EQ-1001 --[subject_to]--> OISD-116"])
    assert "EQ-1001" in res["answer"]


# ── NvidiaLLM (pure config helpers, no network) ───────────────────────────────

def test_build_extra_body_nemotron_thinking():
    llm = NvidiaLLM()
    body = llm._build_extra_body(is_nemotron=True, enable_thinking=True, reasoning_budget=1024)
    assert body == {
        "chat_template_kwargs": {"enable_thinking": True},
        "reasoning_budget": 1024,
    }


def test_build_extra_body_nemotron_no_thinking():
    llm = NvidiaLLM()
    body = llm._build_extra_body(is_nemotron=True, enable_thinking=False, reasoning_budget=0)
    assert body == {"chat_template_kwargs": {"enable_thinking": False}}


def test_build_extra_body_other_model():
    llm = NvidiaLLM()
    assert llm._build_extra_body(is_nemotron=False, enable_thinking=True, reasoning_budget=1024) == {}


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
