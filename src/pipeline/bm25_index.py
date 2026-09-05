import re
import threading
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from loguru import logger


def tokenize_text(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r'\b[a-zA-Z0-9_-]{2,}\b', text.lower())


class BM25Index:
    """In-memory BM25 index for keyword search over document chunks."""

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


# Global singleton index
_global_index = BM25Index()


def get_bm25_index() -> BM25Index:
    """Get the global BM25Index instance."""
    return _global_index
