# Jarvis — Full Rebuild Manual (from an empty folder), with engineering discipline built in

## Before Phase 0: what this manual is and isn't

This is a genuine restart of the *codebase*, not of the *decisions*. The old
repo at `Shivala-08/jarvis` stays exactly where it is — read-only, not
cloned, not touched — purely as a record of what went wrong. Every mistake
found in it is baked into this manual as a thing built correctly the first
time:

| What went wrong last time | What this manual does differently |
|---|---|
| No root `package.json`/`pnpm-workspace.yaml`/`cordis.yml` — nothing ever actually loaded | Built in Phase 1, before any plugin code is written |
| `@deepseek-ai/dsh-type-meta` phantom dependency silently blocked every install | Resolved for real below — pin to the `next` dist-tag, not `latest` |
| Local Ollama models strained a 16GB Mac's RAM/battery | Cloud-first from Phase 2 onward, no local model serving at all |
| Freebuff (third-party cloud coding CLI) wrote unreliable code and shipped your repo to someone else's servers | Never introduced. DSH's own coding-node is the only coding agent, full stop |
| Memory plugin had dead unreachable code and needed a real review pass, not just a compile check | Phase 5 includes an explicit self-review step before anything is considered done |
| Graph orchestrator picked the first matching edge instead of evaluating conditions | Phase 6 specifies real condition evaluation from the first line of code |
| HUD was a stub with no source | Not started until Phase 10, and only after everything it depends on is real |
| **No persistent constitution — nothing stopped an agent session from "improving" the architecture while also adding features, so architecture drifted silently across sessions** | **Phase 0.5, new: AGENTS.md and a docs/ set exist before any plugin code, and every phase from here on runs through one mandated loop instead of improvised prompting** |

**Two decisions carried over from other work this manual assumes — worth being deliberate about, not just absorbing silently:**

1. **Cloud-first models (Phase 3).** This is a real departure from the original "nothing paid, nothing cloud-dependent" principle from early in this project. The trade-off is legitimate — a 16GB Mac genuinely struggles with local inference — but it means Jarvis now depends on external providers and their free-tier quotas rather than being fully self-contained. Worth revisiting once/if the hardware situation changes.
2. **Voice via Voicebox MCP (Phase 4).** This replaces the earlier whisper.cpp/mlx-whisper + Kokoro custom-plugin plan with a single Dockerized MCP server. Simpler to stand up, less to maintain, one more Docker service to keep running.

---

## Phase 0 — Local folder, not a clone

```bash
mkdir jarvis && cd jarvis
git init
git remote add reference https://github.com/Shivala-08/jarvis.git
git fetch reference --no-tags
# reference/main and reference/jarvis-dsh now exist as read-only history
# you can browse (git show reference/jarvis-dsh:path/to/file) without
# ever checking them out or merging them in
```

This gives you the old code as a queryable reference without it being part
of your new working tree. If you want to pull one specific old file in
later (say, the HUD's design tokens, which were fine), `git show
reference/jarvis-dsh:ui/orb/orb.js > reference-orb.js` and review it before
deciding whether to actually use it.

**Exit check:** `git log --oneline -5` on your new repo is empty except
Phase 0's own commits. `git branch -a` shows `reference/*` branches you
never `checkout -b` from directly.

---

## Phase 0.5 — The constitution and discipline layer (new — before any plugin code)

**Why this phase exists:** the single highest-leverage finding from the
engineering-discipline research done alongside this rebuild is that most
AI-assisted projects don't collapse because the model is weak — they
collapse because nothing constrains the *development loop*. An agent left
to both add features and "improve architecture" in the same session drifts.
This phase installs the constraints before Phase 1 writes a single line of
plugin code, so nothing downstream is ever built without them.

### 1. Freeze the architecture, in writing, before features start

Create `docs/ARCHITECTURE.md` seeded with the actual shape of this system —
not inferred later, stated now so no agent session ever has to guess it:

```
JARVIS
│
├── UI              (Holographic Core, HUD, Panels, Animations — Phase 10)
├── Voice            (Voicebox MCP — Phase 4)
├── Agent             (Intent, Planning, Tool Selection, Memory — Phases 5, 6, 7)
├── Tools              (Coding, Browser, Files, System — Phase 7)
└── Infrastructure      (Config, Logging, Errors, Tests — every phase)
```

No agent session may reorganize this tree while also implementing a
feature. Restructuring, if it's ever genuinely needed, is its own task with
its own review — never a side effect of an unrelated change.

### 2. `AGENTS.md` — the permanent constitution, at repo root

```markdown
# JARVIS ENGINEERING RULES
## Core Principle
Never make broad changes when a local change will solve the problem.
## Before Coding
1. Inspect the relevant files.
2. Understand existing architecture (docs/ARCHITECTURE.md is authoritative).
3. Identify dependencies.
4. Produce a short implementation plan.
5. Identify risks.
6. Do not modify code until the plan is understood.
## Scope
Every task must have a clearly defined scope. Do not:
- rewrite unrelated components
- rename files unnecessarily
- replace libraries without approval
- change architecture during feature implementation
- modify working code merely for stylistic reasons
## Implementation
Prefer small changes, existing abstractions, existing dependencies,
composable components, explicit interfaces, predictable state management.
Avoid unnecessary abstractions, duplicate functionality, global state
unless already established, massive files, magic constants, speculative
features.
## Validation
After every meaningful change:
1. Run the relevant tests.
2. Run lint/type checking.
3. Build the plugin(s) affected.
4. Verify the affected behavior directly (not just "it compiles").
5. Inspect the git diff.
Never claim a task is complete without validation — "it compiles" and
"it's done" are different claims. This exact gap is what let the old
memory plugin's dead code through last time.
## Failure Handling
When something fails, do NOT immediately rewrite the implementation.
Instead: reproduce the failure, read the error completely, identify the
root cause, determine the smallest fix, apply only that fix, re-run the
failing test, run regression tests.
## Git
One logical change = one commit. Never reset, delete, or overwrite
unrelated work. Branch per feature (feature/ui, feature/voice,
feature/agent, feature/tools) off main; merge only validated work.
## Architecture
docs/ARCHITECTURE.md is authoritative. Do not introduce a new pattern
when an existing one solves the problem. Do not restructure
docs/ARCHITECTURE.md's tree as a side effect of a feature task.
```

### 3. The mandated loop — used for every phase from here on

```
RESEARCH → PLAN → IMPLEMENT → TEST → REVIEW → (pass? no → DEBUG) → COMMIT → next task
```

Concretely, as prompts:
- **Read:** *"Do not modify anything. Inspect the repository and identify the files relevant to this task."*
- **Plan:** *"Based on the existing architecture, produce an implementation plan. Do not write code yet."*
- **Implement:** *"Implement only the approved plan. Do not modify unrelated files."*
- **Verify:** *"Run the relevant tests, type checker, linter and build. If anything fails, diagnose the root cause and fix only what is necessary."*
- **Review:** *"Review your own diff as a senior engineer. Look specifically for regressions, unnecessary changes, broken state management, duplicated logic and architecture violations."*

Feature-sized prompts ("make the UI more futuristic and add voice control
and memory") are the single biggest way this collapses — each of those is
20 engineering tasks pretending to be one. One task, one coherent diff, one
commit.

### 4. Role separation — whoever builds it doesn't sole-review it

This generalizes what Phase 5 already requires for the memory plugin and
Phase 7 already requires via `verification-agent`, into a standing rule for
everything: a plan-only **Architect** pass, a **Builder** pass that
implements only the approved plan, a **Tester** pass that writes the
expected-behavior test *before* implementation where practical (tests as a
contract, not just a bug detector — the AI isn't inventing what "working"
means, it's building against a spec), and an **independent Reviewer** pass
whose explicit job is to find reasons the change should *not* be merged,
not to confirm it looks fine. The same session doing all four is the weak
version of this — use a second DSH session for the Reviewer pass wherever
the change touches anything in Infrastructure or Agent from the frozen
architecture tree.

### 5. Stability tiers — not everything deserves the same caution

```
src/
├── ui/experimental/   ← tolerates rapid iteration, sphere/glow/animations/layout
├── core/stable/        ← voice, agent, memory, tools, permissions, filesystem, auth
├── services/stable/
└── tools/isolated/
```

UI experimentation may change rapidly. Core services must preserve stable
interfaces. This is the concrete reason Phase 10 (HUD) is last in this
manual and Phases 5–7 (memory, orchestration, coding-agent) get the
review discipline from point 4 above — they're in the tier that isn't
allowed to be vibe-coded freely.

### 6. Context-collapse protocol

Long sessions eventually start forgetting earlier decisions, inventing new
patterns, contradicting existing code, duplicating components. The fix is
never a better model mid-session — it's a fresh session, re-grounded with:
`AGENTS.md` + `docs/ARCHITECTURE.md` + the current task + the current git
diff + current test results, opened with: *"You are continuing an existing
project. Do not infer architecture from this conversation. Use the
repository and AGENTS.md as the source of truth."* Don't keep pushing a
degrading session past the point where it's contradicting its own earlier
output — that's the signal to restart, not push through.

**Exit check for this phase:** `AGENTS.md` and `docs/ARCHITECTURE.md` (plus
empty `docs/DECISIONS.md`, `docs/STATE.md`, `docs/TESTING.md` stubs) exist
and are committed before Phase 1 begins. Hand a fresh DSH session nothing
but these files and a trivial question about the project — it should
correctly describe Jarvis's architecture without you explaining anything
further.

---

## Phase 1 — DSH install, with the phantom dependency actually resolved

**The fix, confirmed by checking the npm registry directly:**
`@deepseek-ai/dsh-session`, `dsh-tools`, and `dsh-user-approval` are all
clean of the `dsh-type-meta` reference on their `next` dist-tag
(`0.1.1-rc.2`) — it only exists in the stale `latest` (`0.0.1-rc.1`)
snapshot, left over from a mid-rename. Pin to `next` explicitly rather than
letting the wildcard peer dependencies resolve to `latest`:

```json
{
  "pnpm": {
    "overrides": {
      "@deepseek-ai/dsh-session": "0.1.1-rc.2",
      "@deepseek-ai/dsh-tools": "0.1.1-rc.2",
      "@deepseek-ai/dsh-user-approval": "0.1.1-rc.2"
    }
  }
}
```

Add this to root `package.json` (Phase 2 creates the full file — this block
goes in it) *before* running `pnpm install` for the first time.

**Then install:**
```bash
git clone https://github.com/deepseek-ai/deepseek-harness.git dsh-source
cd dsh-source && pnpm install && pnpm run build
git log -1 --format="%H" > ../DSH_VERSION_PINNED.txt
cd ..
```

**Exit check:** `npx @deepseek-ai/dsh web` starts cleanly, loads at
`127.0.0.1:3080`, and `pnpm why @deepseek-ai/dsh-type-meta` (run from
wherever you eventually mount plugins) returns nothing found — confirming
the override actually took effect, not just that install didn't crash for
an unrelated reason.

---

## Phase 2 — Root workspace, built correctly from the first commit

```
jarvis/
├── AGENTS.md            # from Phase 0.5
├── docs/                # from Phase 0.5
├── package.json
├── pnpm-workspace.yaml
├── cordis.yml
├── plugins/
├── vault/              # Obsidian mirror, gitignored .obsidian/ subfolder
└── DSH_VERSION_PINNED.txt
```

`package.json` (includes Phase 1's override block):
```json
{
  "name": "jarvis",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "pnpm -r --filter='./plugins/*' run build",
    "clean": "pnpm -r --filter='./plugins/*' exec rm -rf dist"
  },
  "pnpm": {
    "overrides": {
      "@deepseek-ai/dsh-session": "0.1.1-rc.2",
      "@deepseek-ai/dsh-tools": "0.1.1-rc.2",
      "@deepseek-ai/dsh-user-approval": "0.1.1-rc.2"
    }
  },
  "devDependencies": { "typescript": "^5.0.0", "tsup": "^8.0.0" },
  "engines": { "node": ">=18" }
}
```

`pnpm-workspace.yaml`:
```yaml
packages:
  - "plugins/*"
```

`cordis.yml` — starts empty except a comment; each phase below appends its
own plugin entry as it's built, so this file's history *is* the build log:
```yaml
# Plugins get appended here phase by phase. Nothing is ever added to this
# file for a plugin that doesn't yet pass its own phase's exit check.
plugins: []
```

**Git branching, from this point on:** `main` stays merge-only. Work
happens on `feature/ui`, `feature/voice`, `feature/agent`, `feature/tools`
— one branch per area from the frozen architecture tree, merged only after
that area's phase passes its exit check.

**Exit check:** `pnpm install` from repo root succeeds with zero errors,
zero warnings about missing workspace packages (there are none yet — that's
expected and fine).

---

## Phase 3 — Cloud model layer (no local serving, multi-provider, quota-aware)

```
plugins/dsh-jarvis-models/
  src/
    provider-catalog.ts   # Groq, Gemini, OpenRouter-free, Cerebras (verify card status first)
    cloud-router.ts        # picks provider, fails over on error/429
    quota-tracker.ts       # tracks daily free-tier usage per provider, routes around exhaustion proactively
```

Register each provider as a `dsh-llm`-compatible plugin entry in
`cordis.yml`. Three tiers, same shape as originally planned, just cloud
instead of local:
- **Routing tier** — fastest/cheapest (Groq)
- **Everyday tier** — balance of quality and quota (Gemini, largest free context)
- **Coding tier** — whichever provider currently gives the best free coding-model access; re-evaluate this choice periodically since free-tier model lineups shift

**Exit check:** a chat request through DSH visibly hits an external
provider's API in the logs, and killing your network mid-`quota_tracker`
test shows the router failing over to a second provider rather than the
whole system hanging.

---

## Phase 4 — Voice via Voicebox MCP (no custom TTS/STT plugins)

```bash
git clone https://github.com/jamiepine/voicebox.git voicebox-source
cd voicebox-source && docker compose up -d
curl http://127.0.0.1:17493/health   # confirm before wiring into cordis.yml
```
Add the `mcp-voicebox` entry to `cordis.yml` (`serverName: voicebox`,
`transport: streamable-http`, `url: http://127.0.0.1:17493/mcp`).

**Exit check:** DSH's startup log shows `mcp-voicebox` connected and lists
registered tool names — confirm the actual sanitized name before wiring
anything to call it (resolve it at runtime by substring match, don't
hardcode a guess).

---

## Phase 5 — Memory (Cognee + Qdrant), with a real review pass this time

1. Cognee for graph memory (Kuzu embedded store, no separate DB server needed), Qdrant for vector search, wrapped as a single `dsh-jarvis-memory` Cordis plugin.
2. **Role separation from Phase 0.5 applies here specifically:** before this phase is marked done, a *second* DSH session — not the one that wrote the plugin — reads `remember()`, `recall()`, and `forget()` line by line as the independent Reviewer, explicitly looking for reasons not to merge it. "It compiles" is not "it's done" — that gap is exactly what let the old plugin's dead code and hardcoded path through last time.
3. Shadow-mode migration doesn't apply this time (no prior Mem0 data to migrate from a deleted codebase) — one less risk to carry.

**Exit check:** ask something requiring recall of a fact stored earlier in
the *same* session, confirm the answer traces to Cognee's graph, and
confirm the independent review pass actually happened and found (or ruled
out) dead code paths — not skipped because the happy-path test passed.

---

## Phase 6 — Graph orchestrator, with real edge evaluation from line one

The bug last time: `EDGES.find(e => e.from === currentNode && e.condition
!== 'always')` — picks the *first* edge matching the current node,
ignoring whether the edge's actual condition is true. Build it correctly
from the start:

```typescript
function selectNextEdge(edges: Edge[], currentNode: string, state: GraphState): Edge | null {
  const candidates = edges.filter(e => e.from === currentNode)
  for (const edge of candidates) {
    if (edge.condition === 'always') return edge
    if (evaluateCondition(edge.condition, state)) return edge  // actually evaluated, not just checked for existence
  }
  return null
}
```

Nodes: `braindump-node`, `scheduler-node`, `body-double-node`,
`coding-node` — same roster as originally planned, this phase is about
correct routing between them, not new nodes.

**Exit check:** construct a test case with two edges from the same node,
different conditions, confirm the graph picks the one whose condition is
actually true — not just the first one defined in the edge list.

---

## Phase 7 — Coding-agent, built on native DSH primitives + reliability hardening

Per the Coding OS analysis: don't build 8 custom plugins. `dsh-goal`,
`dsh-plan-mode`, `dsh-todo`, `dsh-fs-search`, `dsh-lsp`, `dsh-compaction`,
`dsh-shell`, `dsh-sandbox`, `dsh-subagent` are already native and more
mature than a from-scratch build. What you actually build:

1. **`jarvis-project-memory`** — the one real gap, a `.jarvis/decisions.md` the coding agent writes to itself after non-trivial choices.
2. **`jarvis-debug-agent`, `jarvis-verification-agent`, `jarvis-ship-agent`** — subagents built on `dsh-subagent`.
3. **From the reliability research:**
   - Hard step cap (15 steps) with mandatory human escalation before continuing further
   - Span-level tracing plugin — every tool call and model invocation logs `{step, tool, reasoning_summary, input, output, duration_ms}` to an append-only local file, separate from DSH's own session-log checkpointing
   - `verification-agent` is a hard gate, not advisory — `ship-agent` structurally cannot proceed if verification's status isn't `ready`

**Operating procedure for this phase, from Phase 0.5's discipline layer:**
this is where the mandated loop and role separation matter most, since this
is Core/stable territory. `task-planner` runs the Read+Plan steps as the
Architect role (plan-only, no code written yet). `coding-agent` is the
Builder, implementing only the approved plan. Write the expected-behavior
test *before* implementation where practical — that's `jarvis-verification-agent`
being given a contract to build against, not just a bug detector run
afterward. `verification-agent`'s gate is the Tester role's output; route
its failures through Failure Handling from `AGENTS.md` (reproduce, read the
error fully, smallest fix, re-run) rather than letting `debug-agent`
rewrite broadly. Route non-trivial completions through an independent
Reviewer pass — a fresh subagent session whose job is finding reasons *not*
to ship — before `ship-agent` is even invoked.

**Exit check:** the full loop — "build X with tests" → plan → implement →
verify → debug if needed → independent review → ship with your
confirmation — completes without you manually invoking any individual
step, and the trace log shows a readable why for every action taken along
the way.

---

## Phase 8 — Identity intake, wired in from day one

Paste your answers to the identity-intake questionnaire into
`vault/Identity.md` now, before building anything user-facing. Every graph
node's system prompt (Phase 6) includes this file's contents by default —
build that injection in from the start rather than retrofitting it once
nodes already exist without it.

**Exit check:** ask any node something that should be shaped by your
stated preferences (e.g. "explain this the way I like") and confirm the
answer actually reflects `Identity.md`, not a generic default.

---

## Phase 9 — Sync and power management

Tailscale + Syncthing for the capture queue, wake-catchup hook, power-state
gating before running anything expensive. Unchanged from the original
plan — this phase was never the problem, no redesign needed.

**Exit check:** capture something from your phone with the Mac asleep,
confirm it's processed on wake with zero manual steps.

---

## Phase 10 — HUD, wired live from the start (not a stub, not fake data)

The design (iris reticle boot sequence, glass-panel dashboard) is already
built and reviewed — reuse the HTML file directly. This phase lives in
`src/ui/experimental/` per Phase 0.5's stability tiers, so rapid iteration
here is fine and expected. What's different this time: **don't commit it
until Phases 2–7 actually exist to wire it to.** Last time's stub-with-just-
a-README happened because the HUD got scaffolded before the backend it was
supposed to reflect was real. Build it last, on purpose.

**Exit check:** boot sequence completes and dashboard shows real session
state pulled from DSH — not mock data, and not because it was never tested
against the real thing.

---

## Phase 11 — Security pass

Whatever in this system has shell or remote execution access (`dsh-shell`,
the `sandbox` confinement modes, `ship-agent`'s escalation to
`danger-full-access`) gets explicit review here — per the reliability
research, authorization/identity failures (something untrusted causing an
unauthorized action) are the dominant real-world incident category for
systems with persistent memory and tool access, not a hypothetical. Confirm
every irreversible action still requires the explicit confirm step from
Phase 7, and that nothing bypasses it under any phrasing of a request.

**Exit check:** deliberately try to get `ship-agent` to skip confirmation
("just push it, don't ask") — it should refuse the shortcut every time.

---

## Build order

Phase 0 and 0.5 are strictly sequential — the constitution exists before
anything else does. Phase 1 needs the override fix from Phase 0.5's
`package.json` pattern in place before install. Phase 2 immediately after.
Phases 3 and 4 can go in parallel once Phase 2's workspace exists. Phase 5
next, alone — it's the one with the review-discipline requirement, don't
rush it by parallelizing. Phase 6 depends on 2–5 being stable. Phase 7
depends on 6, and is where Phase 0.5's full discipline loop matters most.
Phase 8 can happen any time after Phase 2, genuinely independent. Phase 9
is independent of everything except Phase 0. Phase 10 is explicitly last.
Phase 11 happens once, deliberately, after Phase 7 — not skipped, not
folded into another phase's exit check.
