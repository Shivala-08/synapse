"""Synapse — AI-Powered Knowledge Intelligence — Configuration."""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "Synapse"
    app_version: str = "1.0.0"
    debug: bool = True

    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Path(__file__).resolve().parent.parent / "data"
    corpus_dir: Path = data_dir / "corpus"
    benchmarks_dir: Path = data_dir / "benchmarks"

    # Database
    database_url: str = Field(default="sqlite:///data/synapse.db", description="Database connection URL")

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # ChromaDB
    chroma_persist_dir: str = str(
        Path(__file__).resolve().parent.parent / "data" / "chroma_db"
    )
    chroma_collection: str = "industrial_docs"

    # Chunking
    chunk_size: int = 1024
    chunk_overlap: int = 200

    # RAG
    top_k: int = 50
    similarity_threshold: float = 0.55

    # LLM — Anthropic
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    llm_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 640

    # LLM — NVIDIA NIM (OpenAI-compatible) — up to 10 keys, tried in order
    nvidia_api_key_1: str = Field(default="", description="NVIDIA NIM API key 1")
    nvidia_api_key_2: str = Field(default="", description="NVIDIA NIM API key 2")
    nvidia_api_key_3: str = Field(default="", description="NVIDIA NIM API key 3")
    nvidia_api_key_4: str = Field(default="", description="NVIDIA NIM API key 4")
    nvidia_api_key_5: str = Field(default="", description="NVIDIA NIM API key 5")
    nvidia_api_key_6: str = Field(default="", description="NVIDIA NIM API key 6")
    nvidia_api_key_7: str = Field(default="", description="NVIDIA NIM API key 7")
    nvidia_api_key_8: str = Field(default="", description="NVIDIA NIM API key 8")
    nvidia_api_key_9: str = Field(default="", description="NVIDIA NIM API key 9")
    nvidia_api_key_10: str = Field(default="", description="NVIDIA NIM API key 10")
    nvidia_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # spaCy
    spacy_model: str = "en_core_web_sm"

    # Feature flags — used by run_ablation.py to isolate retrieval components
    use_reranker: bool = True
    use_hybrid: bool = True
    use_graph: bool = True
    use_semantic_cache: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
