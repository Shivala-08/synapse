# Jarvis — Cloud Model Layer (Phase 3)

Multi-provider cloud model routing with quota awareness. Replaces local Ollama with cloud-first architecture.

## Provider Catalog

| Provider | Tier | Status | Key Feature |
|---|---|---|---|
| Groq | Routing | Active | Fastest inference |
| Gemini | Coding | Active | 2M token context window |
| OpenRouter | Everyday | Conditional | Model variety |
| Cerebras | Routing | Conditional | Speed |

## Architecture

```
Cloud Router → Provider Catalog → Quota Tracker → Failover
```

- **Routing tier:** Fastest/cheapest (Groq)
- **Everyday tier:** Balance of quality and quota (Gemini)
- **Coding tier:** Best free coding-model access

## Key Components

1. **`openai-adapter-base.ts`** — Reusable HTTP fetch, SSE parsing, OpenAI chunk translation
2. **`quota-tracker.ts`** — Tracks daily free-tier usage, routes around exhaustion
3. **`cloud-router.ts`** — Preference-based ranking, health filtering, failover

## Verification

- 17 tests passing across 5 spec files
- DSH web starts successfully on port 3080
- Failover works on network failure and mid-stream drops

## Key Takeaways

- Cloud-first eliminates local model RAM strain on 16GB Macs
- Quota tracking prevents silent exhaustion
- Failover ensures system doesn't hang on provider errors
- [[memory-system]] depends on this layer for LLM calls
