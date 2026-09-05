"""Test ChromaDB integration with a dummy document.

Run: python -m tests.test_chromadb
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.chroma_store import VectorStore
from src.pipeline.embedder import TextEmbedder


def test_chromadb_with_dummy_document():
    """Test that ChromaDB can store and retrieve a dummy document."""
    print("=" * 60)
    print("ChromaDB Integration Test")
    print("=" * 60)

    # 1. Initialize embedder
    print("\n[1/4] Loading embedding model...")
    embedder = TextEmbedder()
    print(f"  ✓ Model loaded: {embedder.model_name} (dim={embedder.dim})")

    # 2. Dummy document content
    dummy_text = """
    Safety Manual Section 3: Equipment Inspection Requirements.
    All equipment tagged EQ-1001 through EQ-4002 must undergo quarterly inspections.
    Pressure vessels TNK-T01, TNK-T02, TNK-T03 require annual internal inspection.
    Pumps PUMP-A01 and PUMP-A02 must be checked monthly for vibration levels.
    Compressors COMP-C01 requires weekly safety checks per OISD-116.
    """

    # 3. Embed the document
    print("\n[2/4] Embedding dummy document...")
    embedding = embedder.embed_texts([dummy_text])
    print(f"  ✓ Generated embedding: {len(embedding[0])} dimensions")

    # 4. Store in ChromaDB
    print("\n[3/4] Storing in ChromaDB...")
    store = VectorStore(collection_name="test_collection")
    store.add_documents(
        ids=["dummy_doc_001"],
        embeddings=embedding,
        documents=[dummy_text.strip()],
        metadatas=[{"source": "dummy_test", "doc_type": "safety_manual"}],
    )
    print(f"  ✓ Stored. Collection count: {store.count()}")

    # 5. Query ChromaDB
    print("\n[4/4] Querying ChromaDB...")
    query_text = "Which equipment requires quarterly inspection?"
    query_embedding = embedder.embed_query(query_text)
    results = store.query(query_embedding, n_results=1)

    print(f"  Query: '{query_text}'")
    print(f"  Retrieved document: {results['documents'][0][0][:100]}...")
    print(f"  Distance: {results['distances'][0][0]:.4f}")

    # 6. Cleanup
    store.delete_all()
    print("\n" + "=" * 60)
    print("✓ ALL CHROMADB TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    test_chromadb_with_dummy_document()
