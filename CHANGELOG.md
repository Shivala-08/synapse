# Changelog

All notable changes to Synapse, in reverse chronological order. Entries before
the revamp are reconstructed from the git history and `archive/conclusions.md`.

## [Unreleased] — Portfolio Revamp (2026-08)

### Repo identity & cleanup
- Renamed project framing from "ET AI Hackathon 2026 submission" to an
  independent R&D project (`economic-times-hackathon` → `synapse`).
- Removed hackathon-only root files (`hackathon_submission.md`, pitch decks,
  `PRESENTATION_SUMMARY.md`); backed up outside the repo. Archived the roadmap
  and the optimization-pass report under `archive/`.
- Added `CHANGELOG.md` and `EVALUATION.md`.

### Evaluation harness
- Expanded `data/benchmarks/qa_pairs.json` (18 → 40 questions) tagged by eval
  category (`factual_lookup` 23, `multi_hop` 9, `compliance_gap` 6,
  `contradiction` 2); all facts verified against the corpus.
- Added Recall@5 and MRR retrieval metrics to `run_benchmark_now.py` and
  exposed ranked candidates from `retrieve_context()`.
- Added `run_ablation.py` — 5-configuration ablation (vector-only → +BM25 →
  +reranker → +graph → full) behind feature flags in `src/config.py`.
- Committed `data/benchmarks/ablation_results.json` from a real run (LLM
  disabled to isolate retrieval). Full pipeline: 62.5% acc / 0.875 R@5 /
  0.667 MRR / 207 ms. Key findings: the reranker is the largest accuracy
  contributor (16/18 on the original set) at +200 ms and lower CSV-record MRR;
  the knowledge graph saves 6 questions and breaks 5; multi-hop questions are
  the honest weak spot. See `EVALUATION.md`.

### Data & retrieval fixes
- **Fixed:** committed ChromaDB index contained all-zero embeddings (built when
  the HF Inference API was unreachable and the old embedder silently fell back
  to zero vectors). Rebuilt the index offline with the local embedder.
- **Fixed:** embedder now falls back to local `sentence-transformers` instead of
  returning zero vectors when the HF Inference API is unavailable.
- Cleaned the knowledge graph: spaCy PERSON/ORG junk filter (roman numerals,
  single letters, fragments, column-spanning spans), graph node type completion
  (previously 25 entities rendered as untyped), rebuilt from the corpus.
  Nodes 1,032 → 533; person nodes 710 → 211.

### Engineering hygiene
- `_extract_personnel()` crash fix (`names.add` on a list → `AttributeError`).
- `sentence-transformers` restored to `requirements.txt` (cross-encoder
  re-ranking silently disabled on fresh installs); dropped stale `streamlit-agraph`.
- Unit-test suite grew from 7 → 105 tests (extractor, chunker, llm, query
  engine, knowledge graph).

### Phase 5 — UI evidence trace & pipeline visual
- Backend now emits a per-stage `trace` dict (cache hit/miss, hybrid on/off,
  reranker on/off, candidate & chunk counts, graph entities/relations,
  complexity, thinking, model, latency) on `/query` and `/query/stream`.
- `/query/stream` now *reads* the semantic cache up front (previously it only
  wrote to it), so duplicate queries stream the cached answer instantly and the
  Cache stage of the pipeline visual can actually HIT.
- New `pipeline_trace()` + `evidence_stats_row()` UI helpers; chat answers now
  show a Query → Cache → Hybrid Retrieve → Rerank → Graph → LLM → Answer step
  row inside a collapsible **"Why this answer?"** panel with retrieval stats and
  citations. Trace is persisted with each chat message.

### Phase 6 — Case study
- Added `docs/CASE_STUDY.md`: problem, architecture, key engineering decisions,
  results (ablation table + LLM-enabled numbers), and an honest "what I'd do
  differently" section.

## 2026-07 — ET AI Hackathon build (original project)

Reconstructed highlights from `archive/conclusions.md` and git history:

- **Day 1–3:** Core RAG pipeline — multi-format parser (PDF/DOCX/CSV/TXT),
  token chunking (1024 + 200 overlap), `all-MiniLM-L6-v2` embeddings in
  ChromaDB, spaCy+regex entity extraction into a NetworkX knowledge graph.
- **Day 4:** Real LLM integration (Ollama → NVIDIA NIM), `/benchmark/run` and
  `/feedback` endpoints, streaming SSE answers.
- **Three-tier optimization:** accuracy 77.8% → 100% (18/18) and latency
  10.3s → 771ms via graph context from chunks, cross-encoder re-ranking,
  semantic cache, per-query complexity routing, and streaming.
- **Resilience:** 10-key NVIDIA rotation with mid-stream failover, smart-context
  fallback, Docker + Render deployment, scanned-PDF handling for OISD-GDN-192.
