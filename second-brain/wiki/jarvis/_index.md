# Jarvis

Jarvis is an AI assistant system rebuilt from scratch with engineering discipline. Cloud-first models, persistent memory, and reliability hardening.

## Articles

- [[cloud-model-layer]] — Multi-provider cloud model routing with quota awareness
- [[memory-system]] — Cognee + Kuzu + LanceDB for persistent graph memory
- [[graph-orchestrator]] — Condition-based routing between four nodes
- [[coding-agent]] — Built on native DSH primitives with reliability hardening

## Architecture

```
UI (Phase 10) → Voice (Phase 4) → Agent (Phases 5-7) → Tools (Phase 7) → Infrastructure
```

## Key Takeaways

- Cloud-first eliminates local model RAM strain
- Embedded stores avoid infrastructure overhead
- Condition evaluation must check state, not just filter
- Don't rebuild what DSH already provides natively
- Structural gates are stronger than prompt-based gates
