# Jarvis — Coding Agent + Reliability Layer (Phase 7)

Built on native DSH primitives with reliability hardening.

## What We Built

1. **`jarvis-project-memory`** — Decision tracking in `.jarvis/decisions.md`
2. **`jarvis-tracing`** — Span-level trace logger + step budget + workflow controller

## What We Didn't Build (DSH-Native)

`dsh-goal`, `dsh-plan-mode`, `dsh-todo`, `dsh-fs-search`, `dsh-lsp`, `dsh-compaction`, `dsh-shell`, `dsh-sandbox`, `dsh-subagent` — all native and more mature than a from-scratch build.

## Workflow State Machine

```
PLAN → IMPLEMENT → VERIFY → REVIEW → SHIP
```

**Legal transitions only.** Illegal transitions throw `IllegalTransitionError`.

## Hard Gates

1. **Verification gate** — `canShip()` returns false unless `verification.status === 'ready'` AND review passed
2. **Step cap** — 15 steps maximum, then `StepCapExceededError`
3. **ShipBlockedError** — Structural gate prevents skipping verification

## Role Separation

- **Architect** — Plan-only, no code written
- **Builder** — Implements only approved plan
- **Tester** — Writes expected-behavior tests before implementation
- **Reviewer** — Independent pass finding reasons NOT to merge
- **Ship** — Only after all gates pass

## Tracing

Append-only JSONL with: step, tool, reasoning_summary, input, output, duration_ms. Separate from DSH session logs.

## Verification

- 31 tests passing (10 decisions + 21 workflow)
- Structural verification gate confirmed
- No shortcut to SHIP possible

## Key Takeaways

- Don't rebuild what DSH already provides natively
- Structural gates (code-enforced) are stronger than prompt-based gates
- Step caps prevent runaway agents
- Independent review catches issues the builder misses
- [[memory-system]] feeds into this for persistent context
