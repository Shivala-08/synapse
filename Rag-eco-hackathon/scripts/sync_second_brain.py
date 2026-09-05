#!/usr/bin/env python3
"""Re-sync the Second Brain domain (non-destructive by default).

Scans the domain's source path (the Obsidian wiki) and ingests any supported
file that is not already in the domain registry. Never deletes or overwrites
existing documents. Mirrors the logic of the POST /ingest/re-sync endpoint so
the vault can be synced without running the API server.

Use --rebuild to wipe the domain's derived index (vector collection, registry,
graph, DB rows) and re-ingest everything from source. This is safe: the index
is derived data and the source path is authoritative.

Usage:
    python scripts/sync_second_brain.py [--domain second_brain] [--rebuild]

Prints added / skipped / errors and a final count summary.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_domain_profile  # noqa: E402
from src.database.connection import get_db_session  # noqa: E402
from src.database.models import Document as DbDoc, DocumentChunk as DbChunk  # noqa: E402
from src.pipeline.ingest import IngestionPipeline, doc_id_for_path  # noqa: E402

ALLOWED = {".txt", ".csv", ".pdf", ".docx", ".md", ".pptx"}


def clear_derived_index(pipeline: IngestionPipeline) -> None:
    """Wipe the domain's derived index so a rebuild starts clean."""
    domain_id = pipeline.domain_profile.domain_id if pipeline.domain_profile else None
    old_doc_ids = {d.get("doc_id") for d in pipeline.list_documents()}

    # Vector collection + registry + graph
    pipeline.store.delete_all()
    pipeline.kg.clear()
    if pipeline.registry_path.exists():
        pipeline.registry_path.unlink()

    # Relational rows for the domain's old documents
    if domain_id and old_doc_ids:
        with get_db_session() as db:
            for doc_id in old_doc_ids:
                db.query(DbChunk).filter(DbChunk.doc_id == doc_id).delete()
                db.query(DbDoc).filter(DbDoc.doc_id == doc_id).delete()
        print(f"  Cleared {len(old_doc_ids)} old document rows from relational DB")
    print(f"  Cleared vector collection, registry, and {domain_id or 'global'} graph")


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-sync a domain from its source folder")
    parser.add_argument("--domain", default="second_brain", help="Domain ID (default: second_brain)")
    parser.add_argument("--rebuild", action="store_true",
                        help="Clear the domain's derived index and re-ingest everything from source")
    args = parser.parse_args()

    dp = load_domain_profile(args.domain)
    src = Path(dp.source_path)

    if not src.exists():
        print(f"ERROR: source path does not exist for '{args.domain}': {src}")
        print("       Set ADHD_CURE_ROOT or <DOMAIN>_SOURCE_PATH (see .env.example).")
        return 2

    pipeline = IngestionPipeline(domain_profile=dp)

    if args.rebuild:
        print(f"REBUILD: clearing derived index for '{args.domain}'...")
        clear_derived_index(pipeline)
        print()

    existing = {d.get("doc_id") for d in pipeline.list_documents()}

    added: list[str] = []
    skipped = 0
    errors: list[dict] = []

    print(f"Domain:    {args.domain} ({dp.display_name})")
    print(f"Source:    {src}")
    print(f"Collection:{dp.collection_name}")
    print(f"Indexed:   {len(existing)} documents already in registry")
    print()

    for item in sorted(src.rglob("*")):
        if not item.is_file() or item.name.startswith("."):
            continue
        if item.suffix.lower() not in ALLOWED:
            continue
        if doc_id_for_path(item, src) in existing:
            skipped += 1
            continue
        try:
            res = pipeline.ingest_file(item, copy_to_uploads=False)
            if res.get("status") == "success":
                added.append(item.name)
                print(f"  + {item.name} ({res.get('chunk_count', 0)} chunks)")
            else:
                errors.append({"file": item.name, "error": res.get("error", "unknown")})
                print(f"  ! {item.name}: {res.get('error', 'unknown')}")
        except Exception as e:
            errors.append({"file": item.name, "error": str(e)})
            print(f"  ! {item.name}: {e}")

    print()
    print(f"Added:   {len(added)}")
    print(f"Skipped: {skipped} (already indexed)")
    print(f"Errors:  {len(errors)}")
    if errors:
        for e in errors:
            print(f"  - {e['file']}: {e['error']}")

    # Validation summary
    store = pipeline.store
    kg = pipeline.kg
    print()
    print("── Validation ──────────────────────────────")
    print(f"Registry documents : {len(pipeline.list_documents())}")
    print(f"Vector chunks      : {store.count()}")
    print(f"Graph nodes        : {kg.graph.number_of_nodes()}")
    print(f"Graph edges        : {kg.graph.number_of_edges()}")
    print(f"Synced at          : {datetime.now().isoformat(timespec='seconds')}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())