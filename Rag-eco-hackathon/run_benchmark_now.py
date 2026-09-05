#!/usr/bin/env python3
"""Run the ground-truth Q&A benchmark for a specific domain.

Usage:
    PYTHONPATH=. python run_benchmark_now.py --domain second_brain
    PYTHONPATH=. python run_benchmark_now.py --domain exam_prep
    PYTHONPATH=. python run_benchmark_now.py                 # lists available domains
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

# ── Ensure project root is on sys.path ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings, load_domain_profile, list_domains
from src.pipeline.embedder import TextEmbedder
from src.pipeline.query_engine import retrieve_context, generate_answer, get_vector_store


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_qa_pairs(domain_id: str) -> list[dict]:
    """Load QA pairs from data/benchmarks/qa_pairs_{domain_id}.json."""
    qa_file = settings.benchmarks_dir / f"qa_pairs_{domain_id}.json"
    if not qa_file.exists():
        print(f"ERROR: No benchmark file found at {qa_file}")
        print(f"       Create it with 15-20 questions before running benchmarks.")
        sys.exit(1)
    with open(qa_file, "r", encoding="utf-8") as f:
        return json.load(f)


def _doc_ids(chunks: list[dict]) -> list[str]:
    """Ordered, deduplicated doc_ids from a list of retrieval chunks."""
    seen = set()
    out = []
    for chunk in chunks:
        doc_id = chunk.get("metadata", {}).get("doc_id", "") or ""
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            out.append(doc_id)
    return out


def retrieval_metrics(expected_sources: list[str], candidate_chunks: list[dict]) -> dict:
    """Ranking metrics from the re-ranked candidate list (top 8).

    Returns Recall@5, MRR, and retrieval_success (expected doc anywhere in the
    candidate list). Metrics are computed over the full candidate pool, not the
    top-3 context chunks, so ranking quality is measured, not prompt assembly.
    """
    if not expected_sources:
        # No ground-truth sources: not measured, not assumed passed.
        return {"recall_at_5": None, "mrr": None, "retrieval_success": None}

    ranked = _doc_ids(candidate_chunks)
    top5 = ranked[:5]
    expected = [s.lower() for s in expected_sources]

    def source_at(rank_idx: int) -> bool:
        return any(e in ranked[rank_idx].lower() for e in expected)

    recall_at_5 = 1.0 if any(any(e in d.lower() for e in expected) for d in top5) else 0.0

    mrr = 0.0
    for i, doc in enumerate(ranked):
        if any(e in doc.lower() for e in expected):
            mrr = 1.0 / (i + 1)
            break

    retrieval_success = 1.0 if any(any(e in d.lower() for e in expected) for d in ranked) else 0.0

    return {
        "recall_at_5": round(recall_at_5, 4),
        "mrr": round(mrr, 4),
        "retrieval_success": round(retrieval_success, 4),
    }


def score_question(qa: dict, answer_text: str, context: dict, embedder: TextEmbedder) -> dict:
    """Score a single question against its expected answer.

    Returns dict with similarity, keyword_hit, source_hit, and overall pass/fail.
    """
    expected = qa["answer"].lower()
    answer_lower = answer_text.lower()

    # 1. Keyword overlap
    expected_keywords = set(expected.split())
    matches = sum(1 for kw in expected_keywords if len(kw) > 4 and kw in answer_lower)
    keyword_hit = matches >= max(1, len(expected_keywords) // 4)

    # 2. Semantic similarity (primary)
    emb_expected = embedder.embed_query(qa["answer"])
    emb_got = embedder.embed_query(answer_text)
    dot = np.dot(emb_expected, emb_got)
    norm = np.linalg.norm(emb_expected) * np.linalg.norm(emb_got)
    similarity = float(dot / norm) if norm > 0 else 0.0
    semantic_hit = similarity >= settings.similarity_threshold

    # 3. Source document match (against the top-3 context chunks used in the prompt)
    expected_sources = qa.get("source_docs", [])
    retrieved_docs = _doc_ids(context.get("vector_chunks", []))
    if expected_sources:
        source_hit = any(
            any(es.lower() in rd.lower() for rd in retrieved_docs)
            for es in expected_sources
        )
    else:
        source_hit = True

    passed = semantic_hit and source_hit

    return {
        "similarity": round(similarity, 4),
        "keyword_hit": keyword_hit,
        "source_hit": source_hit,
        "passed": passed,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def run_benchmark(domain_id: str, max_questions: int = 18) -> dict:
    """Run the benchmark for a single domain."""
    print(f"\n{'='*60}")
    print(f"  BENCHMARK: {domain_id}")
    print(f"{'='*60}")

    # Load domain profile
    try:
        profile = load_domain_profile(domain_id)
        print(f"  Domain:     {profile.display_name}")
        print(f"  Collection: {profile.collection_name}")
    except Exception as e:
        print(f"  ERROR loading domain profile '{domain_id}': {e}")
        return {"error": str(e)}

    # Load QA pairs
    qa_pairs = load_qa_pairs(domain_id)
    total = min(len(qa_pairs), max_questions)
    print(f"  Questions:  {total} (of {len(qa_pairs)} available)")
    print(f"  Model:      checking...")
    print()

    # Verify vector store has data
    store = get_vector_store(domain_profile=profile)
    doc_count = store.count()
    print(f"  Vector store: {doc_count} chunks")
    if doc_count == 0:
        print(f"  WARNING: Vector store is empty for domain '{domain_id}'.")
        print(f"           Run ingestion first.")
        return {"error": "empty vector store"}

    # Run benchmark
    embedder = TextEmbedder()
    results = []
    correct = 0
    total_ms = 0
    recall_sum = 0.0
    mrr_sum = 0.0
    retrieval_hits = 0
    metrics_measured = 0
    categories = {"direct_lookup": [0, 0], "cross_reference": [0, 0], "synthesis": [0, 0]}

    for i, qa in enumerate(qa_pairs[:total], 1):
        t0 = time.time()
        question = qa["question"]
        cat = qa.get("category", "unknown")

        # Retrieve context using domain profile
        context = retrieve_context(question, top_k=50, domain_profile=profile)

        # Generate answer (use fast model for benchmarking speed)
        llm_result = generate_answer(question, context, routing_mode="fast")
        answer_text = llm_result.get("answer", "")

        elapsed_ms = int((time.time() - t0) * 1000)
        total_ms += elapsed_ms

        # Score
        score = score_question(qa, answer_text, context, embedder)
        rank = retrieval_metrics(qa.get("source_docs", []), context.get("candidate_chunks", []))
        if rank["recall_at_5"] is not None:
            metrics_measured += 1
            recall_sum += rank["recall_at_5"]
            mrr_sum += rank["mrr"]
            retrieval_hits += rank["retrieval_success"]

        if score["passed"]:
            correct += 1
        if cat in categories:
            categories[cat][0] += 1
            if score["passed"]:
                categories[cat][1] += 1

        status = "PASS" if score["passed"] else "FAIL"
        reason_parts = []
        if not score["source_hit"]:
            reason_parts.append("wrong source")
        if not score["keyword_hit"]:
            reason_parts.append("low keyword overlap")
        if score["similarity"] < settings.similarity_threshold:
            reason_parts.append(f"sim={score['similarity']:.3f}")
        reason = " (" + ", ".join(reason_parts) + ")" if reason_parts else ""

        print(f"  [{i:2d}/{total}] {status} {qa['id']} ({elapsed_ms}ms) sim={score['similarity']:.3f}{reason}")
        print(f"         Q: {question[:70]}...")

        results.append({
            "id": qa["id"],
            "question": question,
            "category": cat,
            "expected": qa["answer"][:200],
            "got": answer_text[:200],
            "similarity": score["similarity"],
            "keyword_hit": score["keyword_hit"],
            "source_hit": score["source_hit"],
            "recall_at_5": rank["recall_at_5"],
            "mrr": rank["mrr"],
            "retrieval_success": rank["retrieval_success"],
            "passed": score["passed"],
            "latency_ms": elapsed_ms,
        })

    # Summary
    accuracy = round(correct / total * 100, 1) if total > 0 else 0.0
    avg_ms = round(total_ms / total) if total > 0 else 0
    recall_at_5 = round(recall_sum / metrics_measured * 100, 1) if metrics_measured else None
    mrr = round(mrr_sum / metrics_measured, 4) if metrics_measured else None
    retrieval_pct = round(retrieval_hits / metrics_measured * 100, 1) if metrics_measured else None

    print(f"\n{'─'*60}")
    print(f"  RESULTS: {correct}/{total} correct ({accuracy}%)")
    print(f"  Avg latency: {avg_ms}ms")
    if recall_at_5 is not None:
        print(f"  Recall@5: {recall_at_5}%   MRR: {mrr}   Retrieval success: {retrieval_pct}%")
    else:
        print("  Recall@5/MRR: N/A — QA pairs have no source_docs ground truth")
    print(f"\n  By category:")
    for cat_name, (cat_total, cat_correct) in categories.items():
        if cat_total > 0:
            cat_pct = round(cat_correct / cat_total * 100, 1)
            print(f"    {cat_name:20s}: {cat_correct}/{cat_total} ({cat_pct}%)")
    print(f"{'─'*60}\n")

    return {
        "domain": domain_id,
        "total": total,
        "correct": correct,
        "accuracy_pct": accuracy,
        "avg_latency_ms": avg_ms,
        "recall_at_5_pct": recall_at_5,
        "mrr": mrr,
        "retrieval_success_pct": retrieval_pct,
        "categories": {k: {"total": v[0], "correct": v[1]} for k, v in categories.items()},
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Synapse benchmark for a specific domain")
    parser.add_argument("--domain", type=str, help="Domain ID to benchmark (e.g. second_brain, exam_prep)")
    parser.add_argument("--max-questions", type=int, default=18, help="Maximum questions to run (default: 18)")
    parser.add_argument("--list", action="store_true", help="List available domains and exit")
    args = parser.parse_args()

    if args.list or not args.domain:
        domains = list_domains()
        print("Available domains:")
        for d in domains:
            try:
                profile = load_domain_profile(d)
                qa_file = settings.benchmarks_dir / f"qa_pairs_{d}.json"
                qa_count = len(json.loads(qa_file.read_text())) if qa_file.exists() else 0
                print(f"  - {d} ({profile.display_name}) — {qa_count} QA pairs")
            except Exception as e:
                print(f"  - {d} (error: {e})")
        if not args.domain:
            sys.exit(0)
        return

    # Run benchmark
    result = run_benchmark(args.domain, max_questions=args.max_questions)

    # Save results (legacy location + Phase 25 benchmark-results/)
    output_dir = settings.benchmarks_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"results_{args.domain}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Results saved to: {output_file}")

    results_dir = PROJECT_ROOT / "benchmark-results"
    results_dir.mkdir(parents=True, exist_ok=True)
    summary_file = results_dir / f"{args.domain}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Results saved to: {summary_file}")

    _write_summary_md(results_dir)

    # Print final summary
    if "error" not in result:
        print(f"\n{'='*60}")
        print(f"  FINAL: {result['domain']} — {result['accuracy_pct']}% accuracy")
        print(f"{'='*60}")


def _write_summary_md(results_dir: Path) -> None:
    """Regenerate benchmark-results/summary.md from the saved per-domain JSONs."""
    lines = [
        "# Benchmark Results",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "| Domain | Questions | Accuracy | Avg Latency | Recall@5 | MRR | Retrieval Success |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for domain_file in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(domain_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "accuracy_pct" not in data:
            continue
        recall = f"{data['recall_at_5_pct']}%" if data.get("recall_at_5_pct") is not None else "N/A"
        mrr = f"{data['mrr']}" if data.get("mrr") is not None else "N/A"
        retr = f"{data['retrieval_success_pct']}%" if data.get("retrieval_success_pct") is not None else "N/A"
        lines.append(
            f"| {data['domain']} | {data['total']} | {data['accuracy_pct']}% | "
            f"{data['avg_latency_ms']}ms | {recall} | {mrr} | {retr} |"
        )
    lines.append("")
    lines.append("## Per-category accuracy")
    lines.append("")
    lines.append("| Domain | Category | Correct/Total | Accuracy |")
    lines.append("|---|---:|---:|---:|")
    for domain_file in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(domain_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        for cat, counts in data.get("categories", {}).items():
            if counts.get("total", 0) == 0:
                continue
            pct = round(counts["correct"] / counts["total"] * 100, 1)
            lines.append(
                f"| {data['domain']} | {cat} | {counts['correct']}/{counts['total']} | {pct}% |"
            )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Accuracy: semantic similarity >= 0.55 AND expected source among the top-3 context chunks.")
    lines.append("- Recall@5 / MRR / retrieval success are computed over the re-ranked candidate list (top 8)")
    lines.append("  against each question's `source_docs` ground truth.")
    lines.append("- Metrics read `N/A` when a QA pair set has no `source_docs`.")
    lines.append("- Runs use the fast routing model (`meta/llama-3.2-11b-vision-instruct`).")
    (results_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary written to: {results_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
