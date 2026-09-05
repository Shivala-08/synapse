"""Synapse — Configuration and domain profile loader."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "Synapse"
    app_version: str = "1.0.0"
    debug: bool = True

    # Security — if admin_api_key is set, destructive/expensive endpoints
    # (/ingest/initialize, /ingest/upload, /benchmark/run, /debug/search)
    # require the X-API-Key header to match. Leave empty for local dev only.
    admin_api_key: str = Field(default="", description="API key guarding destructive endpoints")
    # When true, refuse to start if ADMIN_API_KEY is empty (production safety)
    require_admin_key: bool = Field(default=False, description="Abort startup if ADMIN_API_KEY is not set")
    max_upload_mb: int = 25

    # CORS — comma-separated allowed origins, e.g.
    # "https://your-domain.com,http://localhost:3000".
    # Empty = allow all origins WITHOUT credentials (safe default).
    cors_origins: str = Field(default="", description="Comma-separated CORS allow-list")

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

    # LLM — general
    llm_model: str = ""
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
    # The deep model's first token can take 40s+; timeouts below that make
    # every non-streaming deep query fail into the smart fallback.
    nvidia_timeout_generate: float = Field(default=120.0, description="OpenAI client timeout (s) for non-streaming NIM calls")
    nvidia_timeout_stream: float = Field(default=120.0, description="OpenAI client timeout (s) for streaming NIM calls")
    nvidia_timeout_connect: float = Field(default=10.0, description="Connect timeout (s) for NIM calls")

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


# ── Domain Profile System ────────────────────────────────────────────────────
# One engine, N domains. Each domain profile defines source paths, entity
# types, storage names, and chunking params. The core pipeline (parser,
# chunker, embedder, llm) never sees domains — only the ingestion coordinator
# and storage layer swap collections/graphs based on the active profile.


class DomainProfile(BaseModel):
    """Configuration for a single ingestable domain."""
    domain_id: str
    display_name: str
    source_path: str
    source_types: list[str]
    collection_name: str
    graph_file: str
    entity_types: list[str]
    link_syntax: str = "none"   # "none" or "wikilink"
    chunk_size: int = 1024
    chunk_overlap: int = 200


def load_domain_profile(domain_id: str) -> DomainProfile:
    """Load a domain profile from domains/{domain_id}.yaml."""
    import yaml
    path = settings.project_root / "domains" / f"{domain_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Domain profile not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return DomainProfile(**data)


def list_domains() -> list[str]:
    """Return domain IDs for all .yaml files in domains/."""
    domains_dir = settings.project_root / "domains"
    if not domains_dir.exists():
        return []
    return sorted(p.stem for p in domains_dir.glob("*.yaml"))


def get_active_domain_profile(domain_id: Optional[str] = None) -> DomainProfile:
    """Load a domain profile, falling back to the first available domain."""
    available = list_domains()
    if not available:
        raise RuntimeError(
            "No domain profiles found. Create domains/*.yaml files first."
        )
    target = domain_id if domain_id and domain_id in available else available[0]
    return load_domain_profile(target)
