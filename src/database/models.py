"""SQLAlchemy models for the Synapse V2 database schemas.

Supports both PostgreSQL (pgvector) and SQLite (JSON/TEXT serialization) via a custom dialect decorator.
"""

import json
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint,
    TypeDecorator
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DynamicVector(TypeDecorator):
    """Custom type to support vector embeddings across both SQLite and PostgreSQL.
    
    On PostgreSQL, it translates to the pgvector VECTOR type.
    On SQLite, it translates to a TEXT type containing a serialized JSON list.
    """
    impl = Text
    cache_ok = True

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dim))
            except ImportError:
                # Fallback to Float ARRAY if pgvector is not installed on the system
                from sqlalchemy.dialects.postgresql import ARRAY
                from sqlalchemy import Float
                return dialect.type_descriptor(ARRAY(Float))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        else:
            if isinstance(value, (list, tuple)):
                return json.dumps(list(value))
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return list(value)
        else:
            try:
                return json.loads(value)
            except Exception:
                return value


class Document(Base):
    """Metadata registry of ingested documents."""
    __tablename__ = "documents"

    doc_id = Column(String(255), primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    nodes = relationship("GraphNode", back_populates="document")


class DocumentChunk(Base):
    """Document chunks and vector embeddings."""
    __tablename__ = "document_chunks"

    chunk_id = Column(String(255), primary_key=True)
    doc_id = Column(String(255), ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(DynamicVector(384), nullable=True) # Dimensions for sentence-transformers model
    metadata_json = Column(Text, nullable=False, default="{}") # JSON-serialized string

    # Relationships
    document = relationship("Document", back_populates="chunks")

    @property
    def parsed_metadata(self) -> dict:
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}

    @parsed_metadata.setter
    def parsed_metadata(self, val: dict):
        self.metadata_json = json.dumps(val or {})


class GraphNode(Base):
    """Graph nodes representing entities in the knowledge graph."""
    __tablename__ = "graph_nodes"

    node_id = Column(String(255), primary_key=True)
    node_type = Column(String(100), nullable=False)
    doc_id = Column(String(255), ForeignKey("documents.doc_id", ondelete="SET NULL"), nullable=True)
    domain_id = Column(String(100), nullable=True, index=True)  # scopes node to a domain
    attributes_json = Column(Text, nullable=False, default="{}")  # JSON-serialized string
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="nodes")

    @property
    def attributes(self) -> dict:
        try:
            return json.loads(self.attributes_json or "{}")
        except Exception:
            return {}

    @attributes.setter
    def attributes(self, val: dict):
        self.attributes_json = json.dumps(val or {})


class GraphEdge(Base):
    """Adjacency edge schema mapping connections in the knowledge graph."""
    __tablename__ = "graph_edges"

    source_id = Column(String(255), ForeignKey("graph_nodes.node_id", ondelete="CASCADE"), primary_key=True)
    target_id = Column(String(255), ForeignKey("graph_nodes.node_id", ondelete="CASCADE"), primary_key=True)
    relation = Column(String(100), primary_key=True)
    domain_id = Column(String(100), nullable=True, index=True)  # scopes edge to a domain
    attributes_json = Column(Text, nullable=False, default="{}")

    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation", name="uq_source_target_relation"),
    )

    @property
    def attributes(self) -> dict:
        try:
            return json.loads(self.attributes_json or "{}")
        except Exception:
            return {}

    @attributes.setter
    def attributes(self, val: dict):
        self.attributes_json = json.dumps(val or {})


class SemanticCache(Base):
    """Semantic Cache caching query responses based on embedding proximity."""
    __tablename__ = "semantic_cache"

    cache_key_hash = Column(String(64), primary_key=True)
    query_text = Column(Text, nullable=False)
    query_embedding = Column(DynamicVector(384), nullable=False)
    cached_response_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def cached_response(self) -> dict:
        try:
            return json.loads(self.cached_response_json or "{}")
        except Exception:
            return {}

    @cached_response.setter
    def cached_response(self, val: dict):
        self.cached_response_json = json.dumps(val or {})


class FeedbackLog(Base):
    """User feedback logs for search quality verification."""
    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, default=datetime.utcnow)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False) # +1 or -1
    comment = Column(Text, nullable=True)


class TelemetryLog(Base):
    """Latency metrics instrumentation for API execution monitoring."""
    __tablename__ = "telemetry_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    query_text = Column(Text, nullable=True)
    retrieval_ms = Column(Integer, default=0)
    reranking_ms = Column(Integer, default=0)
    graph_traversal_ms = Column(Integer, default=0)
    llm_generation_ms = Column(Integer, default=0)
    total_latency_ms = Column(Integer, default=0)
    model_used = Column(String(100), nullable=True)
    cache_hit = Column(String(20), default="false") # "true" or "false"
    error_occurred = Column(String(20), default="false")
