import re
import threading
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from loguru import logger


def tokenize_text(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r'\b[a-zA-Z0-9_-]{2,}\b', text.lower())


class BM25Index:
    """In-memory BM25 index for keyword search over document chunks.

    Domain-aware: each domain gets its own BM25 index instance.
    """

    def __init__(self):
        self.bm25 = None
        self.chunk_ids = []
        self.lock = threading.Lock()

    def build(self, chunks: List[Dict[str, Any]]):
        """Build/rebuild the BM25 index with a list of chunks: [{"id": str, "text": str}]."""
        with self.lock:
            self.chunk_ids = [c["id"] for c in chunks]
            tokenized_corpus = [tokenize_text(c["text"]) for c in chunks]
            if tokenized_corpus:
                self.bm25 = BM25Okapi(tokenized_corpus)
                logger.info(f"BM25Index: Successfully built index over {len(chunks)} chunks")
            else:
                self.bm25 = None
                logger.warning("BM25Index: Corpus is empty. BM25 scoring disabled.")

    def get_scores(self, query: str) -> Dict[str, float]:
        """Compute BM25 similarity scores for all indexed chunks against the query."""
        with self.lock:
            if not self.bm25 or not self.chunk_ids:
                return {}
            tokenized_query = tokenize_text(query)
            scores = self.bm25.get_scores(tokenized_query)
            return {self.chunk_ids[i]: float(scores[i]) for i in range(len(self.chunk_ids))}

    def clear(self):
        """Clear the index."""
        with self.lock:
            self.bm25 = None
            self.chunk_ids = []


# Domain-aware BM25 indexes: one per domain to prevent cross-domain contamination
_bm25_indexes: Dict[str, BM25Index] = {}
_global_index = BM25Index()  # Legacy fallback


def get_bm25_index(domain_id: Optional[str] = None) -> BM25Index:
    """Get the BM25 index for a specific domain.

    When domain_id is given, returns a domain-scoped index.
    When None, returns the legacy global index for backward compatibility.
    """
    if domain_id is None:
        return _global_index
    if domain_id not in _bm25_indexes:
        _bm25_indexes[domain_id] = BM25Index()
        logger.info(f"BM25Index: Created domain-scoped index for '{domain_id}'")
    return _bm25_indexes[domain_id]


def rebuild_bm25_for_domain(domain_id: str, chunks: List[Dict[str, Any]]):
    """Rebuild the BM25 index for a specific domain."""
    index = get_bm25_index(domain_id)
    index.build(chunks)
    logger.info(f"BM25Index: Rebuilt index for domain '{domain_id}' with {len(chunks)} chunks")
