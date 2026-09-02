"""Verification script for FastAPI endpoints.

Run: python tests/verify_endpoints.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("=" * 60)
    # 1. Test /health
    print("\n[1/5] Testing health check...")
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    print(f"  ✓ /health: {resp.json()}")

    # 2. Test /documents
    print("\n[2/5] Testing document list...")
    resp = requests.get(f"{BASE_URL}/documents")
    assert resp.status_code == 200, f"List documents failed: {resp.text}"
    docs = resp.json()
    print(f"  ✓ /documents: Found {len(docs)} documents")
    assert len(docs) > 0, "No documents found in registry."

    # 3. Test /documents/{doc_id}
    print("\n[3/5] Testing document detail...")
    doc_id = docs[0]["doc_id"]
    resp = requests.get(f"{BASE_URL}/documents/{doc_id}")
    assert resp.status_code == 200, f"Get document detail failed: {resp.text}"
    detail = resp.json()
    print(f"  ✓ /documents/{doc_id}: {detail['chunk_count']} chunks retrieved")
    assert len(detail["chunks"]) == detail["chunk_count"], "Chunk count mismatch"

    # 4. Test /query (should return mock answer and citations)
    print("\n[4/5] Testing RAG search query...")
    query = "Which equipment requires quarterly inspection?"
    resp = requests.post(f"{BASE_URL}/query", json={"question": query, "top_k": 5})
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    result = resp.json()
    print(f"  ✓ /query: Answer received")
    print(f"    Confidence: {result['confidence']}")
    print(f"    Sources: Found {len(result['sources'])} sources")
    assert len(result["sources"]) > 0, "No sources found for query"
    
    print("\n[5/5] Testing document upload endpoint...")
    # Create a small dummy file to upload
    dummy_filepath = "tests/test_upload.txt"
    with open(dummy_filepath, "w") as f:
        f.write("This is a dummy safety manual section for upload testing.\nValve VAL-V03 must be inspected every 3 months.")
        
    try:
        with open(dummy_filepath, "rb") as f:
            resp = requests.post(f"{BASE_URL}/ingest/upload", files={"files": (dummy_filepath, f, "text/plain")})
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        upload_result = resp.json()
        print(f"  ✓ /ingest/upload: Ingested successfully: {upload_result}")
    finally:
        import os
        if os.path.exists(dummy_filepath):
            os.remove(dummy_filepath)

    print("\n" + "=" * 60)
    print("✓ ALL API TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
