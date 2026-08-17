# Evaluation

How Synapse is measured, and what the numbers actually show.

## TL;DR

- **40-question ground-truth benchmark** across four eval categories: `factual_lookup` (23), `multi_hop` (9), `compliance_gap` (6), `contradiction` (2).
- **5-configuration ablation** shows every component earns its place — but not for free. The cross-encoder re-ranker is the single biggest accuracy contributor (+11 pts on the original 18), and the knowledge graph enables cross-document answers it otherwise misses, while adding latency in both cases.
- Full pipeline: **62.5% accuracy, 0.875 Recall@5, 0.667 MRR, 207 ms/query** — measured *with the LLM disabled* (see [Method](#method) for why, and how to re-run with it enabled).

> Numbers below are from a real run (`data/benchmarks/ablation_results.json`, generated 2026-08-17). Raw per-question data, including the questions the graph saved and lost, is committed in that file.

## The ablation study

Same 40 questions, same scoring, five configurations — each adding one retrieval component:

| Configuration | Acc% | Recall@5 | MRR | Avg latency |
|---|---|---|---|---|
| Vector-only | 60.0 | 0.850 | 0.783 | 12 ms |
| + BM25 hybrid | 62.5 | 0.900 | 0.840 | 6 ms |
| + Cross-encoder reranker | 62.5 | 0.875 | 0.667 | 210 ms |
| + Knowledge graph | 62.5 | 0.900 | 0.840 | 9 ms |
| **Full pipeline** | **62.5** | **0.875** | **0.667** | **207 ms** |

### What each row teaches

- **Vector-only → +BM25 hybrid (+2.5 acc, MRR 0.783 → 0.840):** sparse lexical signal catches exact identifiers (`WO-2026-1001`, `OISD-117`) that dense vectors blur. Cheapest win on the board — ~free.
- **+ Cross-encoder reranker (16/18 on the original set vs 13–14/18 without it):** the reranker is the **largest single accuracy contributor** on regulatory text questions (see split table below). But it also (a) adds ~200 ms/query and (b) **drops source-level MRR (0.840 → 0.667)** — its regulatory-document boost biases ranking away from record-level CSV lookups. Honest tradeoff: worth it for citation quality on text, paid for in latency and CSV-record ranking.
- **+ Knowledge graph:** the graph **saves 6 questions** that vector-only misses (`Q001`, `Q019`, `Q023`, `Q025`, `Q030`, `Q038` — mostly equipment→regulation/plant linking) but **breaks 5** (`Q002`, `Q009`, `Q020`, `Q027`, `Q029` — entity extraction shifts the candidate ranking on single-doc lookups). Net effect is slightly positive with the reranker on, and it is what makes multi-document questions answerable at all.
- **Full pipeline** ≥ vector-only on accuracy and on the original 18 (89% vs 78%), at the cost of latency. There is no free lunch — the value of each component depends on the question mix.

### Split by question era and eval type (full pipeline)

| Split | Pass rate |
|---|---|
| Original 18 (regulatory text) | 16/18 (89%) |
| New 22 (records + multi-hop + gaps) | 9/22 (41%) |
| `factual_lookup` | 19/23 |
| `contradiction` | 2/2 |
| `compliance_gap` | 2/6 |
| `multi_hop` | 2/9 |

`multi_hop` is the honest weak spot: with the LLM disabled, answers are raw retrieved chunks, so questions that require *synthesizing across two documents* mostly fail the semantic-similarity bar. With the LLM enabled, the original 18-question set measured **100%** (see the optimization table in the README). The `contradiction` questions (e.g. "does the safety manual conflict with OISD-117 on TNK-T03?") pass because both conflicting documents get retrieved together.

## Method

### Scoring (per question)

A question **passes** when both hold:

1. **Semantic match** — cosine similarity ≥ 0.55 between the generated answer and the expected answer (same `all-MiniLM-L6-v2` embedder).
2. **Source match** — at least one expected source document appears in the cited sources.

### Metrics

| Metric | Definition |
|---|---|
| **Accuracy** | % of questions passing both criteria above. |
| **Recall@5** | % of questions where at least one chunk from an expected source document appears in the top-5 ranked candidates. Source-level, not chunk-level. |
| **MRR** | Mean reciprocal rank of the first expected-source chunk in the ranked candidates. |
| **Avg latency** | End-to-end wall time per question (retrieval + answer construction), after a 5-query warm-up. |
| **Citation accuracy** | Not yet automated — human-graded. The plan is to check that each cited source actually contains the claim; until then it is not reported as a machine number. |

### Why the ablation runs with the LLM disabled

`run_ablation.py` disables the semantic cache (no answer leakage between configs) and the external LLM, so answers come from the deterministic smart-context fallback. This isolates **retrieval quality** — the thing the ablation is comparing — from LLM stochasticity. Consequence: absolute accuracy is *lower* than production (raw chunk text vs. a synthesized answer). With an LLM enabled, the original 18-question set scores 100%; the ablation is for **relative** comparison.

### Reproduce

```bash
# Offline ablation (LLM disabled, deterministic) — what the table above shows
PYTHONPATH=. python3 run_ablation.py

# LLM-enabled ablation (needs NVIDIA NIM / Ollama reachable)
PYTHONPATH=. python3 run_ablation.py --with-llm

# Single-config benchmark with per-question detail
PYTHONPATH=. python3 run_benchmark_now.py
```

Raw outputs: `data/benchmarks/ablation_results.json`, `data/benchmarks/retrieval_log.json`.

### Environment note for the committed numbers

The committed run was executed in an offline sandbox (no Hugging Face / NVIDIA API access), so it used the local sentence-transformers embedder and the smart-context fallback. Latencies therefore exclude API and LLM round-trips; the relative per-config pattern is the signal, not the absolute ms.
