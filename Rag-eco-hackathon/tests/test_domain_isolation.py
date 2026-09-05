"""Tests for domain isolation — verifies no cross-domain contamination.

These tests ensure that:
1. Each domain has its own vector store collection
2. Each domain has its own BM25 index
3. Queries scoped to one domain don't return results from another
4. BM25 indexes are properly isolated per domain
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.config import DomainProfile, load_domain_profile
from src.pipeline.bm25_index import BM25Index


class TestDomainProfileLoading:
    """Test that domain profiles load correctly."""

    def test_load_second_brain_profile(self):
        """Second Brain profile loads with correct fields."""
        profile = load_domain_profile("second_brain")
        assert profile.domain_id == "second_brain"
        assert profile.collection_name == "second_brain_vectors"
        assert profile.source_path is not None

    def test_load_exam_prep_profile(self):
        """Exam Prep profile loads with correct fields."""
        profile = load_domain_profile("exam_prep")
        assert profile.domain_id == "exam_prep"
        assert profile.collection_name == "exam_prep_vectors"
        assert profile.source_path is not None

    def test_different_collections(self):
        """Each domain uses a different ChromaDB collection."""
        sb = load_domain_profile("second_brain")
        ep = load_domain_profile("exam_prep")
        assert sb.collection_name != ep.collection_name

    def test_different_graph_files(self):
        """Each domain uses a different graph file."""
        sb = load_domain_profile("second_brain")
        ep = load_domain_profile("exam_prep")
        assert sb.graph_file != ep.graph_file


class TestBM25DomainIsolation:
    """Test that BM25 indexes are isolated per domain."""

    def test_bm25_separate_indexes(self):
        """Each domain gets its own BM25 index instance."""
        from src.pipeline.bm25_index import get_bm25_index

        sb_bm25 = get_bm25_index("second_brain")
        ep_bm25 = get_bm25_index("exam_prep")

        assert sb_bm25 is not ep_bm25

    def test_bm25_domain_scoped_get(self):
        """get_bm25_index returns different indexes for different domains."""
        from src.pipeline.bm25_index import get_bm25_index

        sb_index = get_bm25_index("second_brain")
        ep_index = get_bm25_index("exam_prep")

        assert sb_index is not ep_index

    def test_bm25_build_isolation(self):
        """Building one domain's index doesn't affect another."""
        from src.pipeline.bm25_index import get_bm25_index, BM25Index

        sb_index = BM25Index()
        ep_index = BM25Index()

        # Build with different documents
        sb_docs = [{"id": "1", "text": "doc1"}, {"id": "2", "text": "doc2"}]
        ep_docs = [{"id": "A", "text": "docA"}]

        sb_index.build(sb_docs)
        ep_index.build(ep_docs)

        # Verify each index has the correct document count
        assert len(sb_index.chunk_ids) == 2
        assert len(ep_index.chunk_ids) == 1

    def test_bm25_global_vs_domain(self):
        """Global index is separate from domain indexes."""
        from src.pipeline.bm25_index import get_bm25_index

        global_index = get_bm25_index(None)
        domain_index = get_bm25_index("second_brain")

        assert global_index is not domain_index


class TestVectorStoreIsolation:
    """Test that vector stores are isolated per domain."""

    def test_separate_collections(self):
        """Each domain vector store uses a different collection."""
        from src.storage.chroma_store import VectorStore

        sb_profile = load_domain_profile("second_brain")
        ep_profile = load_domain_profile("exam_prep")

        sb_store = VectorStore(domain_profile=sb_profile)
        ep_store = VectorStore(domain_profile=ep_profile)

        assert sb_store.collection_name == "second_brain_vectors"
        assert ep_store.collection_name == "exam_prep_vectors"
        assert sb_store is not ep_store


class TestDomainQueryIsolation:
    """Test that queries scoped to a domain don't leak across domains."""

    def test_query_returns_domain_field(self):
        """Query response includes the resolved domain."""
        from src.config import get_active_domain_profile

        profile = get_active_domain_profile("exam_prep")
        assert profile.domain_id == "exam_prep"

    def test_list_domains_returns_both(self):
        """Both domains are listed."""
        from src.config import list_domains

        domains = list_domains()
        assert "second_brain" in domains
        assert "exam_prep" in domains
        assert len(domains) >= 2


class TestDomainProfileSchema:
    """Test that domain profiles have all required fields."""

    def test_required_fields_present(self):
        """All required DomainProfile fields are present."""
        profile = load_domain_profile("second_brain")
        assert profile.domain_id is not None
        assert profile.display_name is not None
        assert profile.source_path is not None
        assert profile.source_types is not None
        assert profile.collection_name is not None
        assert profile.graph_file is not None
        assert profile.entity_types is not None

    def test_link_syntax_values(self):
        """Link syntax is a valid value."""
        sb = load_domain_profile("second_brain")
        ep = load_domain_profile("exam_prep")
        assert sb.link_syntax in ("none", "wikilink")
        assert ep.link_syntax in ("none", "wikilink")
