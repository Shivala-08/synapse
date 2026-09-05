"""Ingestion pipeline to parse, chunk, embed, and store documents in ChromaDB.

Supports domain-namespaced ingestion via DomainProfile.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

from src.config import settings, DomainProfile
from src.pipeline.parser import parse_file
from src.pipeline.chunker import chunk_text
from src.pipeline.embedder import TextEmbedder
from src.pipeline.extractor import extract_entities
from src.storage.chroma_store import VectorStore, get_doc_type
from src.graph.knowledge_graph import get_knowledge_graph


def doc_id_for_path(file_path: Path, source_root: Optional[Path] = None) -> str:
    """Derive a stable, collision-free document ID for a file.

    Files inside a domain's source root are keyed by their path relative to
    that root (e.g. ``jarvis/_index.md``), so same-named files in different
    folders (e.g. the ``_index.md`` of each topic) stay distinct. Files
    outside the source root fall back to the bare filename.
    """
    file_path = Path(file_path).resolve()
    if source_root is not None:
        try:
            rel = file_path.relative_to(Path(source_root).resolve())
            return rel.as_posix()
        except ValueError:
            pass
    return file_path.name


class IngestionPipeline:
    """Orchestrates parsing, chunking, embedding, entity extraction, and storing files.

    When a DomainProfile is provided, the pipeline writes to the domain's
    collection and graph. Without a profile, it uses the default (backward-
    compatible) collection.
    """

    def __init__(self, domain_profile: Optional[DomainProfile] = None):
        self.domain_profile = domain_profile
        self.source_root = Path(domain_profile.source_path) if domain_profile else None
        self.embedder = TextEmbedder()
        self.store = VectorStore(domain_profile=domain_profile)
        self.kg = get_knowledge_graph(domain_profile)
        # Domain-scoped registry so each domain tracks its own documents
        if domain_profile:
            self.registry_path = settings.data_dir / f"documents_{domain_profile.domain_id}.json"
        else:
            self.registry_path = settings.data_dir / "documents.json"
        self.uploads_dir = settings.corpus_dir / "uploads"
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def _load_registry(self) -> dict:
        """Load document metadata registry from disk."""
        if not self.registry_path.exists():
            return {}
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load document registry: {e}")
            return {}

    def _save_registry(self, registry: dict):
        """Save document metadata registry to disk."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save document registry: {e}")

    def ingest_file(self, file_path: Path, copy_to_uploads: bool = False) -> dict:
        """Ingest a single file (PDF, DOCX, CSV, TXT) into the vector store.

        Args:
            file_path: Path to the file.
            copy_to_uploads: If True, copies the file to the uploads directory.

        Returns:
            Dictionary with status, doc_id, chunk_count.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = file_path.name
        doc_id = doc_id_for_path(file_path, self.source_root)
        suffix = file_path.suffix.lower()

        logger.info(f"Starting ingestion for file: {filename}")

        # 1. Parse the file
        parsed_records = parse_file(file_path)

        # 2. Chunking (use domain-specific sizes when available)
        chunks = []
        chunk_size = self.domain_profile.chunk_size if self.domain_profile else None
        chunk_overlap = self.domain_profile.chunk_overlap if self.domain_profile else None
        if suffix == ".csv":
            # For CSV, each row returned from parse_file is already a chunk
            chunks = parsed_records
        else:
            full_text = parsed_records[0]["text"]
            raw_chunks = chunk_text(full_text, doc_id=doc_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for rc in raw_chunks:
                rc["metadata"]["record_type"] = suffix.lstrip(".")
                chunks.append({
                    "id": rc["id"],
                    "text": rc["text"],
                    "metadata": rc["metadata"]
                })

        if not chunks:
            logger.warning(f"No chunks created for {filename}. Skipping vector storage.")
            return {"doc_id": doc_id, "status": "skipped", "chunk_count": 0}

        # 3. Embed text chunks
        texts_to_embed = [c["text"] for c in chunks]
        embeddings = self.embedder.embed_texts(texts_to_embed)

        # 4. Entity extraction per-chunk & knowledge graph construction
        try:
            if suffix == ".csv":
                # For CSV, process each row (chunk) independently
                entity_count = 0
                for c in chunks:
                    row_text = c["text"]
                    row_metadata = c["metadata"]
                    row_doc_id = c["id"]
                    
                    row_entities = extract_entities(row_text, row_metadata, domain_profile=self.domain_profile)
                    row_entity_count = sum(len(v) for v in row_entities.values())
                    entity_count += row_entity_count
                    
                    # Store entity IDs in chunk metadata for graph retrieval
                    all_entity_ids = []
                    for category, ents in row_entities.items():
                        all_entity_ids.extend(ents)
                    c["metadata"]["entity_ids"] = json.dumps(all_entity_ids)
                    
                    self.kg.add_document_entities(row_doc_id, row_text, row_entities, row_metadata)
                    # Wikilink edges (Second Brain only)
                    if row_entities.get("wikilinks"):
                        self.kg.add_wikilink_entities(row_doc_id, row_entities["wikilinks"], doc_id=row_doc_id)
                logger.info(f"Extracted and graph-linked {entity_count} entities from CSV {filename} row-by-row")
            else:
                # For text files, extract entities per-chunk and store in metadata
                entity_count = 0
                all_entities = {"equipment": [], "regulations": [], "plants": [], "permits": [],
                               "work_orders": [], "incidents": [], "inspections": [], "personnel": [],
                               "hazards": [], "incident_types": [], "permit_types": []}
                for c in chunks:
                    chunk_entities = extract_entities(c["text"], domain_profile=self.domain_profile)
                    chunk_entity_count = sum(len(v) for v in chunk_entities.values())
                    entity_count += chunk_entity_count
                    
                    # Store entity IDs in chunk metadata
                    all_entity_ids = []
                    for category, ents in chunk_entities.items():
                        all_entity_ids.extend(ents)
                        all_entities.setdefault(category, []).extend(ents)
                    c["metadata"]["entity_ids"] = json.dumps(all_entity_ids)
                
                logger.info(f"Extracted {entity_count} entities from {filename} ({len(chunks)} chunks)")
                # Add to knowledge graph using combined entities
                self.kg.add_document_entities(doc_id, "\n".join(texts_to_embed), all_entities, {})
                # Wikilink edges (Second Brain only). Extract from the chunked
                # text first, then fall back to the raw source file — tokenizer
                # decode can space out [[Note]] into "[ [ Note ] ]" in chunks.
                if self.domain_profile and getattr(self.domain_profile, "link_syntax", "none") == "wikilink":
                    from src.pipeline.extractor import extract_wikilinks
                    full_wikilinks = extract_wikilinks("\n".join(texts_to_embed))
                    if not full_wikilinks and file_path.exists():
                        full_wikilinks = extract_wikilinks(
                            file_path.read_text(encoding="utf-8", errors="ignore")
                        )
                    if full_wikilinks:
                        self.kg.add_wikilink_entities(doc_id, sorted(set(full_wikilinks)), doc_id=doc_id)
        except Exception as e:
            logger.error(f"Entity extraction failed for {filename}: {e}")
            entity_count = 0

        # 5. Save to ChromaDB (after metadata updated with entity_ids)
        doc_type = get_doc_type(doc_id)
        for c in chunks:
            c["metadata"]["doc_type"] = doc_type

        ids = [c["id"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        self.store.add_documents(ids, embeddings, texts_to_embed, metadatas)

        # Rebuild/update BM25 index to reflect new ingested documents (domain-aware)
        try:
            from src.pipeline.bm25_index import get_bm25_index, rebuild_bm25_for_domain
            domain_id = self.domain_profile.domain_id if self.domain_profile else None
            index = get_bm25_index(domain_id)
            all_chunks = self.store.collection.get(include=["documents"])
            c_ids = all_chunks.get("ids", [])
            documents = all_chunks.get("documents", [])
            chunks_list = []
            for i in range(len(c_ids)):
                chunks_list.append({
                    "id": c_ids[i],
                    "text": documents[i]
                })
            if domain_id:
                rebuild_bm25_for_domain(domain_id, chunks_list)
            else:
                index.build(chunks_list)
            logger.info(f"BM25Index: Rebuilt successfully after document ingestion (domain={domain_id})")
        except Exception as e:
            logger.error(f"BM25Index: Failed to rebuild index after ingestion: {e}")

        # 6. Persist file copy in data/corpus/uploads if requested
        dest_path = file_path
        if copy_to_uploads and file_path.resolve().parent != self.uploads_dir.resolve():
            dest_path = self.uploads_dir / filename
            shutil.copy2(file_path, dest_path)
            logger.info(f"Copied uploaded file to persistent storage: {dest_path}")

        # Determine relative path for registry storage
        try:
            rel_path = str(dest_path.relative_to(settings.project_root))
        except ValueError:
            rel_path = str(dest_path)

        # 6.5. Synchronize with Relational DB (FastAPI V2 engine)
        try:
            from src.database.connection import get_db_session
            from src.database.models import Document as DbDoc, DocumentChunk as DbChunk
            
            with get_db_session() as db:
                db_doc = db.query(DbDoc).filter(DbDoc.doc_id == doc_id).first()
                if not db_doc:
                    db_doc = DbDoc(
                        doc_id=doc_id,
                        filename=filename,
                        file_path=rel_path,
                        mime_type=suffix.lstrip("."),
                        chunk_count=len(chunks)
                    )
                    db.add(db_doc)
                else:
                    db_doc.chunk_count = len(chunks)
                    db_doc.file_path = rel_path
                    db_doc.mime_type = suffix.lstrip(".")
                
                # Clear existing chunks for clean ups
                db.query(DbChunk).filter(DbChunk.doc_id == doc_id).delete()
                
                for idx, c in enumerate(chunks):
                    db_chunk = DbChunk(
                        chunk_id=c["id"],
                        doc_id=doc_id,
                        chunk_index=c["metadata"]["chunk_index"],
                        content=c["text"],
                        embedding=embeddings[idx]
                    )
                    db_chunk.parsed_metadata = c["metadata"]
                    db.add(db_chunk)
            logger.info(f"Relational DB: Successfully indexed {len(chunks)} chunks for {doc_id}")
        except Exception as db_err:
            logger.error(f"Relational DB index failed for {doc_id}: {db_err}")

        # 7. Update document registry
        registry = self._load_registry()
        registry[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "file_path": rel_path,
            "type": suffix.lstrip("."),
            "upload_date": datetime.now().isoformat(),
            "chunk_count": len(chunks),
            "entities_found": entity_count,
        }
        self._save_registry(registry)

        # Save knowledge graph after each document
        self.kg.save()

        logger.info(f"Successfully ingested {filename} ({len(chunks)} chunks, {entity_count} entities)")
        return {
            "doc_id": doc_id,
            "status": "success",
            "chunk_count": len(chunks),
            "entities_found": entity_count,
        }

    def list_documents(self) -> list[dict]:
        """List all documents currently tracked in the registry."""
        registry = self._load_registry()
        return list(registry.values())

    def initialize_corpus(self) -> dict:
        """Clear vector database, knowledge graph, and re-ingest all corpus files.

        Scans:
        - data/corpus/real/ (Regulatory PDFs/TXTs)
        - data/corpus/synthetic/ (CSV Work Orders/Permits/Inspections)
        - data/corpus/uploads/ (User uploaded documents)
        """
        logger.info("Initializing vector store corpus...")

        # 1. Clear database and knowledge graph
        self.store.delete_all()
        self.kg.clear()
        if self.registry_path.exists():
            try:
                os.remove(self.registry_path)
            except Exception as e:
                logger.error(f"Failed to remove registry file: {e}")

        # 2. Find files in real/ and synthetic/
        real_dir = settings.corpus_dir / "real"
        synth_dir = settings.corpus_dir / "synthetic"
        uploads_dir = settings.corpus_dir / "uploads"

        dirs_to_scan = [real_dir, synth_dir, uploads_dir]
        ingested_count = 0
        total_chunks = 0
        details = []

        for d in dirs_to_scan:
            if not d.exists():
                continue
            for item in d.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    # Check for supported extensions
                    if item.suffix.lower() in [".txt", ".pdf", ".docx", ".csv", ".md", ".pptx"]:
                        try:
                            # Do not need to copy during initialization since they are already in the corpus directories
                            res = self.ingest_file(item, copy_to_uploads=False)
                            if res["status"] == "success":
                                ingested_count += 1
                                total_chunks += res["chunk_count"]
                                details.append(res)
                        except Exception as e:
                            logger.error(f"Error ingesting file {item.name}: {e}")

        # Save knowledge graph once after all files are ingested
        self.kg.save()

        logger.info(f"Corpus initialized successfully: {ingested_count} files, {total_chunks} chunks")
        return {
            "files_ingested": ingested_count,
            "total_chunks": total_chunks,
            "details": details
        }


if __name__ == "__main__":
    # Let's support running the script directly to initialize the corpus
    pipeline = IngestionPipeline()
    res = pipeline.initialize_corpus()
    print(f"Ingestion completed. Files: {res['files_ingested']}, Chunks: {res['total_chunks']}")
