# Synapse — Case Study

**Graph-Augmented Knowledge Intelligence Engine** · RAG + knowledge graphs + adaptive model routing for industrial safety documents

> 🔗 **Live demo:** [pallav-rag-first-project.streamlit.app](https://pallav-rag-first-project.streamlit.app/) · **Source:** [github.com/Shivala-08/synapse](https://github.com/Shivala-08/synapse)
>
> Full engineering narrative: [`ENGINEERING_LOG.md`](../ENGINEERING_LOG.md) · Full evaluation: [`EVALUATION.md`](../EVALUATION.md)

---

## 1. Problem

Industrial safety documentation is heterogeneous and poorly indexed: regulatory guides (OISD, DGMS, Factory Act), scanned PDFs, and CSV work-order/permits logs all live in different formats, and no single keyword search can answer questions that span documents — like "does the safety manual conflict with OISD-117 on tank TNK-T03?" Standard retrieval also misses *compliance gaps*: a requirement may exist in one document while the plant's own procedures never mention it. The goal was a system that ingests this corpus and answers regulatory questions with cited, confidence-scored responses — and proves, with measurements, that it does.

## 2. Architecture

```
Query ──► Semantic Cache (cosine <1ms) ──hit──► Answer
              │ miss
              ▼
        Complexity Classifier ──► Adaptive Router
              │                        ├── Fast: meta/llama-3.1-8b (no thinking)
              │                        └── Deep: nemotron-550b (1024-budget thinking)
              ▼
   ┌───────────────────────────────────────────────┐
   │ Hybrid Retrieval: BM25 + vector fusion        │
   │ Cross-Encoder Re-rank (top-10 → top-3)        │
   │ Knowledge Graph 1-hop traversal (chunk + query)│
   └───────────────────────────────────────────────┘
              │
              ▼
        LLM (NVIDIA NIM / Ollama / smart fallback)
              │
              ▼
   Streaming SSE answer + sources + evidence trace
```

- **Ingestion:** multi-format parsers (PDF/DOCX/CSV/TXT) → token chunking (1024 + 200 overlap) → `all-MiniLM-L6-v2` embeddings in ChromaDB, spaCy + regex entity extraction into a NetworkX knowledge graph.
- **Query:** hybrid BM25+vector fusion, cross-encoder re-ranking, graph traversal anchored on entities from *retrieved chunks* (not just query text), per-query complexity routing, and a 500-entry semantic cache.
- **UI:** Streamlit frontend with streaming answers, an interactive 3D knowledge graph, an evaluation runner, and a "Why this answer?" evidence trace.

## 3. Key Engineering Decisions

1. **Hybrid retrieval (BM25 + dense).** Sparse lexical signal catches exact identifiers (`WO-2026-1001`, `OISD-117`) that dense vectors blur. Cheapest accuracy win on the board: +2.5 pts and MRR 0.783 → 0.840 for ~free (see [`EVALUATION.md`](../EVALUATION.md)).
2. **Cross-encoder re-ranking.** The single largest accuracy contributor (16/18 on the original set vs 13–14/18 without it) — but it costs ~200 ms/query and *hurts* record-level CSV lookups. Kept, with the tradeoff documented honestly.
3. **Knowledge graph anchored on chunk metadata, not query text.** Queries phrased without exact entity names found nothing in the graph until traversal started from entities embedded in *retrieved chunks*. This is what makes cross-document answers (contradiction, multi-hop) possible at all.
4. **Adaptive model routing.** A heuristic complexity classifier gates the 1024-token thinking budget: simple lookups skip it entirely, complex comparisons get it. Part of the 10.3s → 771ms latency collapse.
5. **Fail loudly, not silently.** The two worst production bugs — a vector index silently rebuilt with all-zero embeddings, and a cross-encoder silently disabled by a missing dependency — were both *silent* degradations. The system now falls back loudly (local embedder, visible logging) instead.

## 4. Results

Measured with a 40-question ground-truth benchmark across four eval categories (`factual_lookup`, `multi_hop`, `compliance_gap`, `contradiction`), ablation run with the LLM disabled to isolate retrieval quality:

| Configuration | Acc% | Recall@5 | MRR | Avg latency |
|---|---|---|---|---|
| Vector-only | 60.0 | 0.850 | 0.783 | 12 ms |
| + BM25 hybrid | 62.5 | 0.900 | 0.840 | 6 ms |
| + Cross-encoder reranker | 62.5 | 0.875 | 0.667 | 210 ms |
| + Knowledge graph | 62.5 | 0.900 | 0.840 | 9 ms |
| **Full pipeline** | **62.5** | **0.875** | **0.667** | **207 ms** |

- With the LLM enabled, the original 18-question regulatory set scores **100%** (up from 77.8%), with steady-state latency **10,306 ms → 771 ms** (−92.5%).
- The knowledge graph **saves 6 questions** (equipment→regulation linking) but **breaks 5** (single-doc lookups where graph context shifts ranking). Multi-hop questions are the honest weak spot (2/9 without an LLM to synthesize across documents).

Full per-question data: [`data/benchmarks/ablation_results.json`](../data/benchmarks/ablation_results.json).

## 5. What I'd Do Differently

The retrieval-ablation methodology surfaced the truth: each component earns its place, but *not for free*, and the knowledge graph is the most fragile one — it adds latency and can *hurt* single-document lookups. I would have built the evaluation harness *before* adding the graph and reranker, not after: it took one bad week of "why did accuracy drop?" ghost-chasing to learn that cold-start variance was the culprit, and a committed retrieval log (`retrieval_log.json`) is what finally made regressions diagnosable. I'd also have treated the silent-degradation class of bugs (zero-vector fallback, missing-dependency `except` blocks) as a first-class review checklist from day one — both cost more debugging time than any feature. And for a production version, I'd want an async FastAPI path and real human-graded citation accuracy on every answer, not just the benchmark set.

## 6. Reproduce

```bash
git clone https://github.com/Shivala-08/synapse.git && cd synapse
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Offline unit tests (no API keys, no model downloads)
PYTHONPATH=. python -m pytest tests/test_knowledge_graph.py tests/test_extractor.py \
  tests/test_chunker.py tests/test_llm.py tests/test_query_engine.py -q

# 40-question benchmark + 5-configuration ablation
PYTHONPATH=. python3 run_benchmark_now.py
PYTHONPATH=. python3 run_ablation.py

# Launch the app
./start.sh   # FastAPI :8000 + Streamlit :8501
```
