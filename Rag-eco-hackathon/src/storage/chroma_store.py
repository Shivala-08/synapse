"""ChromaDB vector store wrapper. Supports domain-namespaced collections."""

from pathlib import Path
from typing import Optional, Union
import chromadb
from loguru import logger

from src.config import settings, DomainProfile


def get_doc_type(filename: str) -> str:
    filename_lower = filename.lower()
    if "work_order" in filename_lower or "wo_" in filename_lower or "workorder" in filename_lower:
        return "work_order"
    elif "permit" in filename_lower or "pt_" in filename_lower:
        return "permit"
    elif "incident" in filename_lower or "inc_" in filename_lower:
        return "incident_report"
    elif "sop" in filename_lower:
        return "sop"
    else:
        return "other"


class VectorStore:
    """Manages ChromaDB collections for document embeddings.

    Accepts either a DomainProfile or a plain collection_name string.
    When given a DomainProfile, the collection name comes from the profile.
    """

    def __init__(self, domain_profile: Optional[DomainProfile] = None, collection_name: str = None):
        if domain_profile is not None:
            self.collection_name = domain_profile.collection_name
        else:
            self.collection_name = collection_name or settings.chroma_collection
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"VectorStore initialized: collection='{self.collection_name}'")
        # Defer _ensure_doc_types — it scans all items and adds latency on every init.
        # Run it once lazily on first query instead.
        self._doc_types_checked = False

    def _ensure_doc_types(self):
        """Ensure all stored document chunks have doc_type populated."""
        try:
            all_items = self.collection.get(include=["metadatas"])
            ids = all_items.get("ids", [])
            metadatas = all_items.get("metadatas", [])
            
            if not ids or not metadatas:
                return

            update_ids = []
            update_metadatas = []
            
            for idx, meta in enumerate(metadatas):
                if meta is None:
                    meta = {}
                if "doc_type" not in meta:
                    doc_id = meta.get("doc_id", ids[idx])
                    meta["doc_type"] = get_doc_type(doc_id)
                    update_ids.append(ids[idx])
                    update_metadatas.append(meta)
            
            if update_ids:
                logger.info(f"Ensuring doc_type in metadata: migrating {len(update_ids)} chunks")
                self.collection.update(ids=update_ids, metadatas=update_metadatas)
        except Exception as e:
            logger.error(f"Failed to migrate metadata for doc_type: {e}")

    def add_documents(self, ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]):
        """Add documents with embeddings to the collection."""
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(ids)} documents to vector store")

    def query(self, query_embedding: list[float], n_results: int = 5, where: dict = None) -> dict:
        """Query the collection for similar documents."""
        # Lazy doc_type migration: run once on first query, not on init
        if not self._doc_types_checked:
            self._doc_types_checked = True
            try:
                self._ensure_doc_types()
            except Exception as e:
                logger.warning(f"Lazy doc_type check failed: {e}")
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )
        return results

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self.collection.count()

    def delete_all(self):
        """Delete all documents from the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.warning("All documents deleted from vector store")
