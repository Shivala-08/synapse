#!/usr/bin/env python3
"""Run the 5-configuration ablation study.

Isolates the contribution of each retrieval component by running the same
benchmark with progressively more components enabled:

    vector_only → +BM25 hybrid → +cross-encoder reranker → +knowledge graph → full

For a clean comparison the run disables the semantic cache (no answer leakage
between configs) and the external LLM (answers use the deterministic
smart-context fallback, so accuracy differences reflect retrieval, not LLM
stochasticity). Re-run with an LLM available to measure the LLM-enabled numbers.

Usage:
    PYTHONPATH=. python run_ablation.py
    PYTHONPATH=. python run_ablation.py --qa-file data/benchmarks/qa_pairs.json

Results are saved to data/benchmarks/ablation_results.json.
"""

import argparse
import json
import os
import sys
import time

from src.config import settings
from src.pipeline.llm import reset_llm
from run_benchmark_now import run_benchmark

CONFIGS = [
    {"name": "vector_only", "label": "Vector-only", "use_hybrid": False, "use_reranker": False, "use_graph": False},
    {"name": "hybrid_bm25", "label": "+ BM25 hybrid", "use_hybrid": True, "use_reranker": False, "use_graph": False},
    {"name": "reranker", "label": "+ Cross-encoder reranker", "use_hybrid": True, "use_reranker": True, "use_graph": False},
    {"name": "knowledge_graph", "label": "+ Knowledge graph", "use_hybrid": True, "use_reranker": False, "use_graph": True},
    {"name": "full_pipeline", "label": "Full pipeline", "use_hybrid": True, "use_reranker": True, "use_graph": True},
]


def main():
    parser = argparse.ArgumentParser(description="Run the 5-configuration ablation study")
    parser.add_argument("--qa-file", default="data/benchmarks/qa_pairs.json")
    parser.add_argument("--with-llm", action="store_true",
                        help="Keep the external LLM enabled (slower, needs API access)")
    parser.add_argument("--checkpoint", default="data/benchmarks/ablation_results.json",
                        help="Path to write results; existing entries are resumed from")
    parser.add_argument("--only", default=None,
                        help="Run only this config name (e.g. vector_only); skips others")
    args = parser.parse_args()

    # Resume: load previously completed configs so long runs survive restarts.
    rows, detail = [], {}
    if os.path.exists(args.checkpoint):
        try:
            prev = json.load(open(args.checkpoint))
            rows = prev.get("configs", [])
            detail = prev.get("per_question", {})
            print(f"Resuming from checkpoint: {len(rows)} config(s) already done "
                  f"({[r['config'] for r in rows]}).\n")
        except Exception:
            print("Checkpoint exists but unreadable — starting fresh.\n")

    # Semantic cache is ALWAYS disabled during ablation — with it on, config 1
    # would answer a question and the cache would leak that answer into later
    # configs, masking the very retrieval differences the ablation measures.
    settings.use_semantic_cache = False

    if not args.with_llm:
        # Deterministic local runs: no external LLM either.
        for i in range(1, 11):
            setattr(settings, f"nvidia_api_key_{i}", "")
        reset_llm()
        print("Ablation mode: semantic cache disabled, external LLM disabled "
              "(smart-context fallback used for answers).\n")
    else:
        print("Ablation mode: semantic cache disabled, external LLM ENABLED "
              "(end-to-end numbers; cache off so configs stay independent).\n")

    def _save_checkpoint(rows, detail):
        out = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "qa_file": args.qa_file,
            "question_count": rows[0]["total"] if rows else 0,
            "notes": {
                "semantic_cache": "disabled during ablation (prevents answer leakage between configs)",
                "llm": ("disabled — smart-context fallback used, isolating retrieval quality"
                        if not args.with_llm else "enabled"),
                "embedder": "local sentence-transformers all-MiniLM-L6-v2 (offline run)",
                "scoring": "semantic similarity >= 0.55 AND expected source doc retrieved",
                "recall_mrr_definition": ("source-level: a chunk is relevant if its doc_id "
                                          "contains an expected source document name"),
            },
            "configs": rows,
            "per_question": detail,
        }
        with open(args.checkpoint, "w") as f:
            json.dump(out, f, indent=2)

    for cfg in CONFIGS:
        if args.only and cfg["name"] != args.only:
            continue
        if any(r["config"] == cfg["name"] for r in rows):
            print(f"SKIP {cfg['label']} — already in checkpoint.")
            continue

        settings.use_hybrid = cfg["use_hybrid"]
        settings.use_reranker = cfg["use_reranker"]
        settings.use_graph = cfg["use_graph"]

        print("=" * 70)
        print(f"CONFIG: {cfg['label']}")
        print("=" * 70)

        t0 = time.time()
        report = run_benchmark(qa_file=args.qa_file, warmup=True)
        run_seconds = int(time.time() - t0)

        rows.append({
            "config": cfg["name"],
            "label": cfg["label"],
            "use_hybrid": cfg["use_hybrid"],
            "use_reranker": cfg["use_reranker"],
            "use_graph": cfg["use_graph"],
            "accuracy_pct": report["accuracy_pct"],
            "correct": report["correct"],
            "total": report["total"],
            "recall_at_5": report["avg_recall_at_5"],
            "mrr": report["avg_mrr"],
            "avg_latency_ms": report["avg_latency_ms"],
            "run_seconds": run_seconds,
        })
        detail[cfg["name"]] = report["results"]
        _save_checkpoint(rows, detail)
        print(f"Checkpoint saved ({len(rows)}/{len(CONFIGS)} configs).\n")

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "qa_file": args.qa_file,
        "question_count": rows[0]["total"] if rows else 0,
        "notes": {
            "semantic_cache": "disabled during ablation (prevents answer leakage between configs)",
            "llm": ("disabled — smart-context fallback used, isolating retrieval quality"
                    if not args.with_llm else "enabled"),
            "embedder": "local sentence-transformers all-MiniLM-L6-v2 (offline run)",
            "scoring": "semantic similarity >= 0.55 AND expected source doc retrieved",
            "recall_mrr_definition": ("source-level: a chunk is relevant if its doc_id "
                                      "contains an expected source document name"),
        },
        "configs": rows,
        "per_question": detail,
    }

    out_path = args.checkpoint
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print("\n" + "=" * 70)
    print("ABLATION RESULTS")
    print("=" * 70)
    header = f"{'Config':<28}{'Acc%':>7}{'R@5':>7}{'MRR':>7}{'Avg ms':>9}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['label']:<28}{r['accuracy_pct']:>7}{r['recall_at_5']:>7}{r['mrr']:>7}{r['avg_latency_ms']:>9}")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
