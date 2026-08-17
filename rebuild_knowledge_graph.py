#!/usr/bin/env python3
"""Rebuild the knowledge graph and chunk entity metadata from the existing
ChromaDB index — without re-embedding.

Use after changing entity extraction logic (e.g. the spaCy junk filter) to
refresh:
  - data/knowledge_graph.json
  - chunk "entity_ids" metadata in ChromaDB
  - document registry entity counts (data/documents.json)

The vector embeddings are untouched, so this is fast and needs no network.

Usage:
    PYTHONPATH=. python rebuild_knowledge_graph.py
"""

import json
import sys
from collections import defaultdict

from loguru import logger

from src.config import settings
from src.pipeline.extractor import extract_entities
from src.storage.chroma_store import VectorStore
from src.graph.knowledge_graph import get_knowledge_graph

# record_type values assigned to non-CSV (whole-document) chunks in ingest.py
TEXT_TYPES = {"txt", "pdf", "docx"}


def flatten_entity_ids(entities: dict) -> list:
    """Flatten all extracted entity IDs across categories (mirrors ingest.py)."""
    flat = []
    for ents in entities.values():
        flat.extend(ents)
    return flat


def main():
    store = VectorStore()
    kg = get_knowledge_graph()
    kg.clear()  # start from an empty graph so stale entities are dropped

    all_chunks = store.collection.get(include=["documents", "metadatas"])
    ids = all_chunks.get("ids", [])
    documents = all_chunks.get("documents", [])
    metadatas = all_chunks.get("metadatas", [])

    if not ids:
        logger.error("Vector store is empty — nothing to rebuild.")
        sys.exit(1)

    logger.info(f"Rebuilding knowledge graph from {len(ids)} existing chunks (no re-embedding)")

    # Group non-CSV chunks by document; collect CSV rows separately
    doc_chunks = defaultdict(list)   # doc_id -> [(chunk_id, text, metadata)]
    csv_rows = []                    # [(row_id, text, metadata)]

    for i in range(len(ids)):
        meta = metadatas[i] or {}
        record_type = meta.get("record_type", "")
        if record_type in TEXT_TYPES or not record_type:
            doc_chunks[meta.get("doc_id", ids[i])].append((ids[i], documents[i], meta))
        else:
            csv_rows.append((ids[i], documents[i], meta))

    updated_meta = []   # (chunk_id, new_metadata) pairs to persist
    entity_counts = defaultdict(int)  # registry doc_id -> total entities

    # ── CSV rows: per-row extraction + graph links (mirrors ingest.py) ──
    for row_id, text, meta in csv_rows:
        entities = extract_entities(text, meta)
        kg.add_document_entities(row_id, text, entities, meta)
        new_meta = dict(meta)
        new_meta["entity_ids"] = json.dumps(flatten_entity_ids(entities))
        updated_meta.append((row_id, new_meta))
        entity_counts[meta.get("doc_id", "unknown")] += sum(len(v) for v in entities.values())

    # ── Text documents: aggregate entities per doc (mirrors ingest.py) ──
    for doc_id, chunks in doc_chunks.items():
        all_entities = defaultdict(list)
        texts = []
        for chunk_id, text, meta in chunks:
            texts.append(text)
            entities = extract_entities(text)
            for category, ents in entities.items():
                all_entities[category].extend(ents)
            new_meta = dict(meta)
            new_meta["entity_ids"] = json.dumps(flatten_entity_ids(entities))
            updated_meta.append((chunk_id, new_meta))
            entity_counts[doc_id] += sum(len(v) for v in entities.values())

        kg.add_document_entities(doc_id, "\n".join(texts), dict(all_entities), {})

    # ── Persist cleaned entity_ids metadata back to ChromaDB ──
    if updated_meta:
        store.collection.update(
            ids=[m[0] for m in updated_meta],
            metadatas=[m[1] for m in updated_meta],
        )
        logger.info(f"Updated entity_ids metadata for {len(updated_meta)} chunks")

    kg.save()
    logger.info(
        f"Knowledge graph saved: {kg.graph.number_of_nodes()} nodes, "
        f"{kg.graph.number_of_edges()} edges"
    )

    # ── Refresh document registry entity counts ──
    registry_path = settings.data_dir / "documents.json"
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load document registry: {e}")
            registry = {}
        changed = 0
        for doc_id, count in entity_counts.items():
            if doc_id in registry and registry[doc_id].get("entities_found") != count:
                registry[doc_id]["entities_found"] = count
                changed += 1
        if changed:
            registry_path.write_text(
                json.dumps(registry, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info(f"Updated entities_found for {changed} documents in registry")
        else:
            logger.info("Document registry entity counts already up to date")


if __name__ == "__main__":
    main()
