#!/usr/bin/env python3
"""Run the full benchmark and report results.

Usage:
    python run_benchmark_now.py                    # Use default qa_pairs.json
    python run_benchmark_now.py --qa-file qa_pairs_new.json   # Use new QnA file

Reports accuracy, latency, embedding similarity, keyword overlap, and the
retrieval metrics Recall@5 and MRR (source-level: a chunk is relevant if it
belongs to an expected source document).

The per-question evaluation lives in `evaluate_question()` so the ablation
runner (`run_ablation.py`) can reuse it without duplicating scoring logic.
"""
import json
import time
import sys
import argparse
import numpy as np
from collections import defaultdict

from src.pipeline.query_engine import retrieve_context, generate_answer
from src.pipeline.llm import get_llm
from src.storage.chroma_store import VectorStore
from src.pipeline.embedder import TextEmbedder
from src.config import settings

# ── Helpers ───────────────────────────────────────────────────────────────────

def expected_source_docs(qa: dict) -> set:
    """Expected source docs for a question (lowercased for matching)."""
    return {str(d).lower() for d in qa.get("source_docs", [])}


def chunk_belongs_to_expected(chunk: dict, expected_docs: set) -> bool:
    """True if a retrieved chunk belongs to one of the expected source docs."""
    if not expected_docs:
        return False
    doc_id = ((chunk.get("metadata") or {}).get("doc_id") or "").lower()
    return any(es in doc_id for es in expected_docs)


def evaluate_question(qa: dict, embedder: TextEmbedder, llm=None) -> dict:
    """Run retrieval + answer generation for one question and return metrics.

    Metrics:
      - passed: semantic similarity >= threshold AND expected source retrieved
      - recall_at_5 / mrr: source-level retrieval metrics over ranked candidates
      - latency_ms: end-to-end wall time for the question
    """
    t0 = time.time()
    question = qa["question"]
    expected = qa["answer"].lower()
    expected_docs = expected_source_docs(qa)

    context = retrieve_context(question, top_k=50)

    # Ranked candidate list (pre top-3 trim) for retrieval metrics
    candidates = context.get("candidate_chunks") or context.get("vector_chunks") or []

    gold_ranks = [
        i for i, c in enumerate(candidates[:5])
        if chunk_belongs_to_expected(c, expected_docs)
    ]
    recall_at_5 = 1.0 if gold_ranks else 0.0
    mrr = 1.0 / (gold_ranks[0] + 1) if gold_ranks else 0.0

    llm_result = generate_answer(question, context)

    answer_text = llm_result.get("answer", "")
    sources_list = llm_result.get("sources", [])
    retrieved_source_docs = {s.get("citation", s.get("doc_id", "")) for s in sources_list}

    elapsed_ms = int((time.time() - t0) * 1000)

    # 1. Keyword overlap scoring (kept for comparison)
    expected_keywords = set(expected.split())
    answer_lower = answer_text.lower()
    matches = sum(1 for kw in expected_keywords if len(kw) > 4 and kw in answer_lower)
    hit_text_keyword = matches >= max(1, len(expected_keywords) // 4)

    # 2. Embedding similarity scoring
    emb_expected = embedder.embed_query(qa["answer"])
    emb_got = embedder.embed_query(answer_text)
    val_dot = np.dot(emb_expected, emb_got)
    val_norm = (np.linalg.norm(emb_expected) * np.linalg.norm(emb_got))
    similarity = val_dot / val_norm if val_norm > 0 else 0.0
    hit_text_semantic = similarity >= settings.similarity_threshold
    hit_text = hit_text_semantic  # semantic similarity is the primary text criterion

    hit_source = True
    if expected_docs:
        hit_source = any(
            any(es in rs.lower() for rs in retrieved_source_docs)
            for es in expected_docs
        )

    hit = bool(hit_text and hit_source)

    reason = []
    if not hit_text:
        reason.append(f"semantic similarity too low ({similarity:.3f} < {settings.similarity_threshold})")
    if expected_docs and not hit_source:
        reason.append("wrong source retrieved")
    if llm_result.get("confidence") == "Low":
        reason.append("low confidence")
    reason_str = ", ".join(reason) if not hit else ""

    # Chunk sources for regression logging
    chunk_sources = []
    for chunk in context.get("vector_chunks", []):
        meta = chunk.get("metadata", {})
        chunk_sources.append({
            "doc_id": meta.get("doc_id", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "distance": round(chunk.get("distance", 0.0), 4),
            "record_type": meta.get("record_type", "unknown"),
            "excerpt": chunk.get("text", "")[:150],
        })

    return {
        "id": qa.get("id", ""),
        "question": question,
        "expected": qa["answer"],
        "got": answer_text[:300],
        "confidence": llm_result.get("confidence", "Low"),
        "passed": hit,
        "reason": reason_str,
        "latency_ms": elapsed_ms,
        "category": qa.get("category", ""),
        "eval_type": qa.get("type", ""),
        "similarity": float(similarity),
        "passed_keyword": bool(hit_text_keyword),
        "recall_at_5": recall_at_5,
        "mrr": mrr,
        "expected_source_docs": list(qa.get("source_docs", [])),
        "retrieved_source_docs": list(retrieved_source_docs),
        "chunk_sources": chunk_sources,
        "llm_sources": sources_list[:3],
    }


def run_benchmark(qa_file: str = "data/benchmarks/qa_pairs.json",
                  max_questions: int = None,
                  warmup: bool = True) -> dict:
    """Run the benchmark over a Q&A file and return aggregate metrics.

    Returns a dict with results, accuracy, latency, Recall@5 and MRR.
    """
    qa_pairs = json.loads(open(qa_file).read())
    if max_questions:
        qa_pairs = qa_pairs[:max_questions]

    store = VectorStore()
    if store.count() == 0:
        print("ERROR: Vector store empty. Run ingest first.")
        sys.exit(1)

    llm = get_llm()
    embedder = TextEmbedder()
    print(f"Vector store: {store.count()} chunks")
    print(f"LLM: {type(llm).__name__} | model={getattr(llm, 'model', None)} | available={llm.available}")

    # Warm-up phase for consistent latency numbers
    if warmup:
        WARMUP_QUERIES = [
            "Which equipment requires quarterly inspection?",
            "What are the PPE requirements for mining workers?",
            "When is a hot work permit required?",
            "How quickly must serious factory accidents be reported?",
            "What are the electrical safety requirements per OISD-130?",
        ]
        print(f"Warming up with {len(WARMUP_QUERIES)} queries...")
        warmup_start = time.time()
        for wq in WARMUP_QUERIES:
            ctx = retrieve_context(wq, top_k=50)
            _ = generate_answer(wq, ctx)
        print(f"Warm-up complete ({int((time.time() - warmup_start) * 1000)}ms total). Starting benchmark.\n")

    print(f"Running {len(qa_pairs)} questions...\n")
    results = [evaluate_question(qa, embedder, llm) for qa in qa_pairs]

    total = len(results)
    correct = sum(1 for r in results if r["passed"])
    accuracy = round(correct / total * 100, 1) if total else 0.0
    avg_ms = round(sum(r["latency_ms"] for r in results) / total) if total else 0
    avg_recall5 = round(sum(r["recall_at_5"] for r in results) / total, 3) if total else 0.0
    avg_mrr = round(sum(r["mrr"] for r in results) / total, 3) if total else 0.0

    # Retrieval log for regression diagnosis
    retrieval_log = [
        {k: r[k] for k in ("id", "question", "expected_source_docs", "retrieved_source_docs",
                           "chunk_sources", "llm_sources", "similarity")}
        for r in results
    ]
    status_by_id = {r["id"]: ("PASS" if r["passed"] else "FAIL") for r in results}
    for entry in retrieval_log:
        entry["status"] = status_by_id.get(entry["id"], "FAIL")
    log_path = "data/benchmarks/retrieval_log.json"
    with open(log_path, "w") as f:
        json.dump(retrieval_log, f, indent=2)

    return {
        "total": total,
        "correct": correct,
        "accuracy_pct": accuracy,
        "avg_latency_ms": avg_ms,
        "avg_recall_at_5": avg_recall5,
        "avg_mrr": avg_mrr,
        "model_used": getattr(get_llm(), "model", None) or "smart-fallback",
        "results": results,
        "retrieval_log": retrieval_log,
    }


def main():
    parser = argparse.ArgumentParser(description="Run benchmark with specified Q&A file")
    parser.add_argument("--qa-file", default="data/benchmarks/qa_pairs.json",
                        help="Path to Q&A JSON file (default: data/benchmarks/qa_pairs.json)")
    parser.add_argument("--max-questions", type=int, default=None,
                        help="Limit the number of questions to run")
    args = parser.parse_args()

    qa_file = args.qa_file
    if not qa_file.startswith("/") and not qa_file.startswith("data/"):
        qa_file = f"data/benchmarks/{qa_file}"
    print(f"Using Q&A file: {qa_file}")

    report = run_benchmark(qa_file, max_questions=args.max_questions)
    results = report["results"]
    correct, total, accuracy = report["correct"], report["total"], report["accuracy_pct"]
    avg_ms, avg_recall5, avg_mrr = (report["avg_latency_ms"], report["avg_recall_at_5"],
                                    report["avg_mrr"])

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        kw_str = "kw=PASS" if r["passed_keyword"] else "kw=FAIL"
        print(f"[{r['id']}] {status} | {r['latency_ms']:5d}ms | conf={r['confidence']} | "
              f"sim={r['similarity']:.3f} ({kw_str}) | R@5={r['recall_at_5']:.0f} MRR={r['mrr']:.3f} | "
              f"{r['question'][:50]}...")
        if not r["passed"] and r["reason"]:
            print(f"        -> {r['reason']}")
            print(f"        Expected: {r['expected']}")
            print(f"        Got:      {r['got']}")

    print("\n" + "=" * 70)
    print(f"RESULTS: {correct}/{total} correct ({accuracy}%)")
    print(f"RECALL@5: {report['avg_recall_at_5']:.3f} | MRR: {report['avg_mrr']:.3f}")
    print(f"AVG LATENCY: {avg_ms} ms per question")
    print("=" * 70)

    cat_stats = defaultdict(lambda: {"pass": 0, "fail": 0})
    for r in results:
        cat = r.get("category", "other")
        cat_stats[cat]["pass" if r["passed"] else "fail"] += 1
    print("\nCATEGORY BREAKDOWN:")
    for cat, s in sorted(cat_stats.items()):
        total_cat = s["pass"] + s["fail"]
        pct = round(s["pass"] / total_cat * 100) if total_cat > 0 else 0
        print(f"  {cat:<25s} {s['pass']}/{total_cat} ({pct:3d}%)")

    print(f"\nRetrieval log saved to: data/benchmarks/retrieval_log.json")


if __name__ == "__main__":
    main()
