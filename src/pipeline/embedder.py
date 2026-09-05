"""Text embedding using the Hugging Face Inference API, with a local
sentence-transformers fallback.

Primary path: HF Inference API (serverless-friendly, low memory — used on
deployments like Render where loading PyTorch locally caused OOM).

Fallback path: if the API is unreachable (offline, DNS blocked, rate-limited),
embed with a local SentenceTransformer instead. This guarantees embedding
never silently degrades to zero vectors, which would corrupt retrieval.
"""

import os
import time
import httpx
from functools import lru_cache
from loguru import logger

from src.config import settings


class TextEmbedder:
    """Generates embeddings using Hugging Face Inference API, falling back to a
    local SentenceTransformer when the API is unavailable."""

    # Class-level tri-state: None = unknown, True/False = cached availability
    _hf_ok = None

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model
        self.dim = settings.embedding_dim
        # Read Hugging Face token from environment variables if available
        self.hf_token = os.getenv("HF_TOKEN", "")
        self.api_url = (
            f"https://api-inference.huggingface.co/pipeline/feature-extraction/"
            f"sentence-transformers/{self.model_name}"
        )
        self._local_model = None
        logger.info(f"TextEmbedder initialized for model: {self.model_name}")

    def _get_local_model(self):
        """Lazily load the local SentenceTransformer fallback (cached model)."""
        if self._local_model is None:
            from sentence_transformers import SentenceTransformer
            model_id = f"sentence-transformers/{self.model_name}"
            logger.info(f"Loading local SentenceTransformer fallback: {model_id}")
            self._local_model = SentenceTransformer(model_id)
        return self._local_model

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        """Embed with the local model (offline fallback)."""
        model = self._get_local_model()
        embeddings = model.encode(texts, normalize_embeddings=False)
        return [list(map(float, e)) for e in embeddings]

    def _try_hf_api(self, texts: list[str]) -> list[list[float]]:
        """Attempt the HF Inference API for a batch of texts.

        Returns a full list of embeddings on success, or None if the API is
        unavailable (after retries) — in which case the caller falls back.
        """
        if TextEmbedder._hf_ok is False:
            return None

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
                        timeout=30.0,
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
                        logger.warning(
                            f"HF Model loading. Waiting {estimated_time:.1f}s "
                            f"(attempt {attempt + 1}/{retries})..."
                        )
                        time.sleep(min(estimated_time, 10.0))
                    else:
                        raise ValueError(
                            f"HF API returned status {response.status_code}: {response.text}"
                        )
                except Exception as e:
                    logger.warning(
                        f"HF embedding attempt {attempt + 1}/{retries} failed: {e}"
                    )
                    time.sleep(1.5)

            if not success:
                logger.warning(
                    f"HF Inference API unavailable (batch {i // batch_size + 1}). "
                    "Falling back to local embedder for this and future calls."
                )
                TextEmbedder._hf_ok = False
                return None

        TextEmbedder._hf_ok = True
        return all_embeddings

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts (HF API, local fallback)."""
        if not texts:
            return []

        result = self._try_hf_api(texts)
        if result is not None:
            return result
        return self._embed_local(texts)

    @lru_cache(maxsize=128)
    def _cached_embed_query(self, query: str) -> list[float]:
        res = self.embed_texts([query])
        if not res or len(res[0]) != self.dim:
            # A zero/garbage vector would silently corrupt retrieval AND the
            # semantic cache. Fail loudly instead — callers already handle
            # exceptions.
            raise RuntimeError(
                f"Embedding failed for query (got {0 if not res else len(res[0])} dims, expected {self.dim})."
            )
        return res[0]

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a single query."""
        return self._cached_embed_query(query)
