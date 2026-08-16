"""Text embedding using Hugging Face Inference API to save memory in production."""

import os
import time
import httpx
from functools import lru_cache
from loguru import logger
from src.config import settings

class TextEmbedder:
    """Generates embeddings using Hugging Face Inference API (serverless-friendly)."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model
        self.dim = settings.embedding_dim
        # Read Hugging Face token from environment variables if available
        self.hf_token = os.getenv("HF_TOKEN", "")
        self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/{self.model_name}"
        logger.info(f"Hugging Face Embedder initialized for model: {self.model_name}")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts in batches using HF Inference API."""
        if not texts:
            return []

        headers = {}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"

        # Process in batches of 32 to avoid size limits or timeouts
        batch_size = 32
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            retries = 3
            success = False
            
            for attempt in range(retries):
                try:
                    response = httpx.post(
                        self.api_url,
                        headers=headers,
                        json={"inputs": batch},
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        embeddings = response.json()
                        # Verify shape and convert to list of lists
                        if isinstance(embeddings, list) and len(embeddings) > 0:
                            if not isinstance(embeddings[0], list):
                                embeddings = [embeddings]
                            all_embeddings.extend(embeddings)
                            success = True
                            break
                        else:
                            raise ValueError(f"Invalid response format: {embeddings}")
                    elif response.status_code == 503:
                        # Model is currently loading, wait and retry
                        load_info = response.json()
                        estimated_time = load_info.get("estimated_time", 20.0)
                        logger.warning(f"HF Model loading. Waiting {estimated_time:.1f}s (attempt {attempt+1}/{retries})...")
                        time.sleep(min(estimated_time, 10.0))
                    else:
                        raise ValueError(f"HF API returned status {response.status_code}: {response.text}")
                except Exception as e:
                    logger.error(f"HF embedding generation error on attempt {attempt+1}: {e}")
                    time.sleep(1.5)

            if not success:
                # If all retries failed, log warning and return mock zero vectors so ingestion doesn't crash
                logger.warning(f"Failed to generate embeddings for batch {i//batch_size + 1}. Filling with zero vectors.")
                all_embeddings.extend([[0.0] * self.dim for _ in batch])

        return all_embeddings

    @lru_cache(maxsize=128)
    def _cached_embed_query(self, query: str) -> list[float]:
        res = self.embed_texts([query])
        return res[0] if res else [0.0] * self.dim

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query."""
        return self._cached_embed_query(query)
