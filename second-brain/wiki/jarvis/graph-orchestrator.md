# Jarvis — Graph Orchestrator (Phase 6)

Condition-based routing between four nodes with real edge evaluation.

## Nodes

| Node | Purpose |
|---|---|
| `braindump-node` | Captures thoughts, extracts actionable items |
| `scheduler-node` | Organizes tasks, sets priorities |
| `body-double-node` | Accountability partner |
| `coding-node` | Executes coding tasks |

## Routing Rules

```typescript
function selectNextEdge(edges, currentNode, state) {
  const candidates = edges.filter(e => e.from === currentNode)
  for (const edge of candidates) {
    if (edge.condition === 'always') return edge
    if (evaluateCondition(edge.condition, state)) return edge
  }
  return null
}
```

**Critical:** Conditions are EVALUATED against GraphState, not merely checked for existence. The banned anti-pattern `edges.find(e => e.condition !== 'always')` is NOT used.

## Precedence

1. Conditional matches (evaluated true) — highest priority
2. "always" edges — fallback
3. No match — return null

## Cycle Protection

`max_steps` prevents infinite loops. Graph executor tracks traversal depth.

## Verification

- 63 tests across 4 spec files
- Original bug regression test confirms correct behavior
- Edge-order independence verified

## Key Takeaways

- Condition evaluation must actually check state, not just filter for non-"always"
- First TRUE wins for deterministic tie-breaking
- Every transition is logged for debugging
- [[coding-agent]] uses this for task routing
