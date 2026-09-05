# Synapse — Graph-Augmented RAG Intelligence Engine

Hybrid retrieval system with knowledge graph augmentation. Ingests heterogeneous documents and answers questions with cited, confidence-scored responses.

## Architecture

```
Raw Corpus → Parser → Chunker → Embedding → Vector Store (ChromaDB)
                    ↓
              Entity Extraction → Knowledge Graph (NetworkX)
                    ↓
User Query → Adaptive Router → Hybrid Search (BM25 + Vector + CrossEncoder Reranking)
                    ↓
              LLM (NVIDIA NIM / Ollama / Smart Fallback) → Answer with Citations
```

## Core Components

### Pipeline
- **Parser** — TXT, PDF, DOCX, CSV parsing via pdfplumber, python-docx, pandas
- **Chunker** — Paragraph/sentence boundary chunking (configurable size)
- **Embedder** — SentenceTransformer (all-MiniLM-L6-v2, 384 dims)
- **Extractor** — spaCy + regex entity extraction, wikilink parsing

### Storage
- **ChromaDB** — Vector store with cosine similarity
- **NetworkX** — Knowledge graph with domain-namespaced nodes/edges
- **BM25** — Keyword search index (currently global, needs domain isolation)

### Query Engine
- Hybrid fusion (vector + BM25 with alpha weighting)
- CrossEncoder re-ranking (ms-marco-MiniLM-L-6-v2)
- Graph traversal for related entities
- Semantic caching for repeated queries

## Domain System

One engine, N domains. Domain profiles define:
- Source path and types
- Collection name (vector isolation)
- Graph file (graph isolation)
- Entity types and link syntax
- Chunk size and overlap

## LLM Routing

| Mode | Model | Use Case |
|---|---|---|
| Fast | Llama 3.1 8B | Simple lookups |
| Deep | Nemotron 550B | Complex synthesis |
| Auto | Classifier decides | Default |
| Fallback | Smart Context | No LLM available |

## Key Takeaways

- Vector + graph dual path answers both "what" and "how" questions
- Domain profiles enable multi-tenant isolation on one engine
- [[campushub-fix-instructions]] shows similar architectural patterns
- [[cloud-model-layer]] uses cloud-first approach for LLM routing
