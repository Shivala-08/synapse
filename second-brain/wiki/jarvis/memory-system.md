# Jarvis — Memory System (Phase 5)

Cognee + Kuzu + LanceDB for persistent graph memory and vector search.

## Architecture

- **Cognee** — Graph memory via Kuzu embedded store (no separate DB)
- **LanceDB** — Vector search (embedded, built into Cognee)
- **Cloud-only** — LLM + embeddings via OpenRouter, no local models

## Core Operations

### `remember()`
Store memories via Cognee's full pipeline. Metadata includes timestamp, source, category.

### `recall()`
Hybrid retrieval combining vector similarity and graph traversal. Returns ranked results with relevance scores.

### `forget()`
Clean both graph and vector stores. Supports selective deletion by metadata filters.

## Plugin Structure

```
plugins/dsh-jarvis-memory/
├── src/
│   ├── types.ts      # Memory data model
│   ├── config.ts     # Environment configuration
│   ├── index.ts      # Plugin entry point
│   └── backend.py    # Python Cognee backend
├── docs/
│   ├── memory-contract.md
│   └── memory-storage-boundaries.md
└── tests/
    ├── config.spec.ts   # 10 tests
    └── memory.spec.ts   # 16 tests
```

## Design Decisions

1. **LanceDB over Qdrant** — Embedded, no separate server
2. **Cloud-only** — Eliminates local model complexity
3. **Python subprocess** — Isolates Cognee operations
4. **Typed errors** — Specific classes for different failures

## Verification

- 26 tests passing
- Independent review pass completed
- No dead code paths identified
- No hardcoded paths

## Key Takeaways

- Embedded stores (Kuzu, LanceDB) avoid infrastructure overhead
- Subprocess isolation prevents Python errors from crashing the Node process
- Independent review caught dead code in the previous implementation
- [[graph-orchestrator]] uses this for state persistence
