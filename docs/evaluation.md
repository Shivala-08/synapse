# Synapse — RAG Evaluation & Benchmarks

This document contains evaluation results from running the deterministic RAG ablation harness on a ground-truth dataset.

---

## 1. Ablation Study Results

The harness was executed on a 40-question ground-truth set under five configurations to isolate retrieval quality. The external LLM and semantic cache were disabled (deterministic fallback mode) to eliminate model stochasticity:

| Configuration | Accuracy | Recall@5 | Mean Reciprocal Rank (MRR) | Avg Latency |
|---|---:|---:|---:|---:|
| **Vector-only** | 60.0% | 0.850 | 0.783 | **12 ms** |
| **+ BM25 Hybrid** | 62.5% | 0.900 | 0.840 | **6 ms** |
| **+ Cross-Encoder Reranker** | 62.5% | 0.875 | 0.667 | **210 ms** |
| **+ Knowledge Graph** | 62.5% | 0.900 | 0.840 | **9 ms** |
| **Full Pipeline** | **62.5%** | **0.875** | **0.667** | **207 ms** |

---

## 2. Evaluation Methodology

### 2.1 Dataset & Ground Truth
* **Size:** 40 curated ground-truth Q&A pairs.
* **Categories:** `factual_lookup` (23 queries), `multi_hop` (9 queries), `compliance_gap` (6 queries), `contradiction` (2 queries).
* **Ground Truth:** Each query is mapped to exact expected source files (e.g. `OISD-117`, incident reports).

### 2.2 Metric Definitions
1. **Accuracy:** Percentage of queries that pass both (a) Expected source matches top candidates, and (b) Semantic similarity between generated output and reference answer is >= 0.55.
2. **Recall@5:** Percentage of queries where the expected document is retrieved in the top 5 candidates.
3. **MRR (Mean Reciprocal Rank):** Evaluates candidate ranking position for expected documents.
4. **Latency:** Wall time per query in milliseconds (averaged over 5 warm-ups).

### 2.3 Hardware & Environment
* **CPU:** Apple M3 Pro (12-core)
* **Embedder:** `all-MiniLM-L6-v2` (local SentenceTransformers)
* **Vector DB:** ChromaDB (local persistence)
* **Graph DB:** NetworkX (in-memory serialized)
