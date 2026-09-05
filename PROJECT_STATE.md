# PROJECT STATE — ADHD-CURE Workspace

**Last Updated:** Phase 25/29/30/31/34 Complete (Benchmarks, Automation, README, Architecture, Env)
**Test Status:** 120/120 passing ✅
**Benchmark Status:** Second Brain 66.7% (12/18), Study Materials 77.8% (14/18), Recall@5 100% both
**Overall:** 23/32 phases complete, 5 blocked (27, 35-39), 4 pending (32, 33, 36, 37, 38)

---

## Architecture Overview

```
adhd-cure/
├── Rag-eco-hackathon/     (Synapse — Shared RAG Engine)
├── second-brain/          (Obsidian Vault — Human-readable knowledge base)
├── second-brain-agent/    (AI Librarian — TypeScript CLI agent)
├── PROJECT_STATE.md       (This file)
└── PHASE_RESULTS.md       (Phase completion details)
```

**Data Flow:**
```
Second Brain (raw/) → Agent TUI → wiki/*.md → Synapse Ingestion → Retrieval
                                    ↑
                           Exam Prep (exam_prep_material/)
```

---

## Component 1: Synapse (Rag-eco-hackathon/)

**Status:** ✅ Core engine operational with domain isolation

### What Exists
- **FastAPI backend** (`src/main.py`, 1157 lines) — full RAG query, ingestion, knowledge graph, benchmark endpoints
- **Next.js frontend** (`web/`) — domain-routed rail, Query Console (SSE streaming + signal pulse), Graph Explorer. Streamlit UI removed.
- **Pipeline modules:**
  - `parser.py` (188 lines) — TXT, PDF, DOCX, CSV, **Markdown**, **PPTX** parsing ✅
  - `chunker.py` — paragraph/sentence boundary chunking
  - `embedder.py` — SentenceTransformer (all-MiniLM-L6-v2)
  - `extractor.py` — spaCy + regex entity extraction, wikilink parsing
  - `ingest.py` (341 lines) — orchestration, **domain-aware** ✅
  - `query_engine.py` (816 lines) — hybrid retrieval (vector + BM25 + graph), **domain-aware** ✅
  - `bm25_index.py` (75 lines) — **domain-scoped indexes** ✅ (FIXED)
  - `llm.py` — NVIDIA NIM / Ollama / smart fallback
  - `compliance.py` — document compliance checking
- **Storage:**
  - `chroma_store.py` — **domain-aware** via DomainProfile ✅
  - `knowledge_graph.py` — **domain-aware** via DomainProfile ✅ (DB-backed)
- **Domain profiles:**
  - `domains/second_brain.yaml` (15 lines) — ✅ real source path configured
  - `domains/exam_prep.yaml` (58 lines) — ✅ real source path configured
- **Config** (`src/config.py`) — DomainProfile model, load/list functions ✅
- **Tests:** 7 test files, **107 tests passing** ✅

### API Endpoints (Verified)
| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | ✅ Returns `{"status": "ok"}` |
| `/query` | POST | ✅ Accepts `domain_id`, returns domain-scoped results |
| `/query/stream` | POST | ✅ Streaming with domain support |
| `/domains` | GET | ✅ Lists available domain profiles |
| `/ingest` | POST | ✅ Domain-aware ingestion |
| `/knowledge-graph/stats` | GET | ✅ Graph statistics |

### Recent Fixes (Phase 8-25)
1. **BM25 domain isolation** — rewrote `bm25_index.py` with per-domain indexes
2. **Markdown parsing** — added `.md` support to `parser.py`
3. **PPTX parsing** — added PowerPoint support via python-pptx to `parser.py`
4. **Domain API** — added `domain_id` to query endpoints, `/domains` endpoint
5. **Response model** — added `domain` field to `QueryResponse`
6. **Empty check fix** — vector store count check uses correct domain scope
7. **Benchmark harness** — `run_benchmark_now.py` with `--domain` flag
8. **Benchmark QA pairs** — 18 questions per domain (Direct Lookup, Cross-Reference, Synthesis)
9. **LLM model fix** — `meta/llama-3.1-8b-instruct` deprecated, switched to `meta/llama-3.2-11b-vision-instruct`
10. **Study materials ingestion** — 3 real files (2 PDFs + 1 PPTX) → 23 chunks in exam_prep domain
11. **Knowledge graphs populated** — both domain graphs were empty (0 nodes); `populate_domain_graphs.py` rebuilt them → second_brain 7 notes/6 LINKS_TO edges, exam_prep 46 nodes/55 edges
12. **Hardcoded paths removed** — `config.py` resolves source paths via `<DOMAIN>_SOURCE_PATH` env override → `$VAR` expansion → workspace root (ADHD_CURE_ROOT); YAMLs now use portable relative paths
13. **Benchmark harness upgraded** — Recall@5, MRR, retrieval success computed from the top-8 candidate list; results written to `benchmark-results/` + `summary.md`
14. **Scripts added** — `scripts/compile-and-ingest-second-brain.sh`, `scripts/audit_wiki.py`, `scripts/sync_second_brain.py`

### Data Ingested
- **Second Brain domain:** 10 wiki files → 10 chunks in `second_brain_vectors` collection
- **Study Materials domain:** 3 files (2 PDFs + 1 PPTX) → 23 chunks in `exam_prep_vectors` collection ✅

---

## Component 2: Second Brain (second-brain/)

**Status:** ✅ Wiki compiled, audit complete

### What Exists
- `CLAUDE.md` — librarian instructions (comprehensive)
- `wiki/_master-index.md` — ✅ updated with all topics
- `wiki/campus-hub/` — ✅ 1 article + index
- `wiki/jarvis/` — ✅ 4 articles + index
- `wiki/synapse/` — ✅ 1 article + index
- `raw/` — 4 source files (preserved untouched)
- `output/wiki-audit.md` — ✅ audit report
- `.obsidian/` — Obsidian config

### Wiki Statistics
| Topic | Articles | Wikilinks |
|-------|----------|-----------|
| campus-hub | 1 | 2 |
| jarvis | 4 | 3 |
| synapse | 1 | 2 |
| **Total** | **6** | **7** |

---

## Component 3: Second Brain Agent (second-brain-agent/)

**Status:** ✅ Approval bug fixed, TypeScript compiles

### What Exists
- **TypeScript CLI** — readline-based chat interface
- **OpenRouter integration** — `@openrouter/agent` SDK v0.11.0
- **Tools:** file_read, file_write, file_edit, glob, grep, list_dir, shell
- **Approval:** `requireApproval: true` on file_write/file_edit
- **Vault sandboxing:** assertInsideVault() on write/edit tools
- **Config:** `agent.config.json` — model, vaultDir, approvalPolicy

### Fixes Applied (Phase 1)
1. **Created `src/state.ts`** — file-backed StateAccessor for approval gates
2. **Updated `src/agent.ts`** — passes state to `callModel()`
3. **Updated `src/cli.ts`** — handles approval/rejection flow
4. **TypeScript compiles cleanly** — `npx tsc --noEmit` passes

---

## Study Materials ✅

**Location:** `second-brain/raw/`

| File | Chunks | Topic |
|------|--------|-------|
| `DBMS & SQL - Revision Notes.pdf` | 14 | DBMS foundations, relational design, SQL commands |
| `Java Script Fundamentals – Complete Notes.pdf` | 3 | JS values, numbers, strings, variables, data types |
| `Lecture 2 - SQL Commands -with PostgreSQL-.pptx` | 6 | SQL introduction, DDL/DML/DCL/TCL, PostgreSQL |

**Status:** Ingested into `exam_prep_vectors` collection (23 chunks total)

---

## Integration Points

| Connection | Status | Issue |
|---|---|---|
| Agent → Second Brain vault | ✅ | Approval workflow fixed |
| Agent → wiki/ output | ✅ | Can write after approval |
| Synapse ← wiki/ input | ✅ | 10 files ingested |
| Synapse ← study materials input | ✅ | 3 files (2 PDFs + 1 PPTX) → 23 chunks |
| Synapse domain isolation | ✅ | Vector, BM25, graph all domain-scoped |
| Synapse UI domain switch | ✅ | Selector works in Streamlit |
| Synapse API domain routing | ✅ | `/query` with `domain_id` works |

---

## Known Errors / Remaining Issues

1. **OpenRouter API key** — needed for Agent TUI live testing (Phase 27)
2. **Deployment not started** — provider choice (Railway/Render), credentials, volume config (Phases 32-33, 35-39)
3. **Broken wikilinks in vault** — strict audit finds 7 dangling links (e.g. `[[jarvis-memory]]` vs `memory-system.md`); reported, not auto-fixed
4. **`_index.md` registry collision** — documents are keyed by filename, so same-named `_index.md` files across topic folders overwrite in the registry
5. **Synthesis accuracy** — fast model answers simple lookups well (83%) but misses abstract cross-document synthesis (50%); Recall@5 is 100% both domains

---

## Test Summary

```
Rag-eco-hackathon/tests/
├── test_chromadb.py        ✅ (1 test)
├── test_chunker.py         ✅ (5 tests)
├── test_domain_isolation.py ✅ (13 tests)
├── test_extractor.py       ✅ (52 tests)
├── test_knowledge_graph.py ✅ (25 tests)
├── test_llm.py             ✅ (10 tests)
├── test_query_engine.py    ✅ (14 tests)
└── Total: 120 passed, 0 failed
```

**Agent TUI:** TypeScript compiles cleanly (`tsc --noEmit` passes)

---

## Execution Progress

| Phase | Status | Notes |
|-------|--------|-------|
| 0: Workspace Discovery | ✅ | This file created |
| 1: Agent Approval Fix | ✅ | StateAccessor implemented |
| 2: Second Brain Compilation | ✅ | 6 wiki articles from 4 sources |
| 3: Vault Audit | ✅ | All articles valid |
| 4-7: Domain Architecture | ✅ | Profiles verified |
| 8-12: Storage Isolation | ✅ | BM25 fixed, all stores domain-aware |
| 13-15: Domain-Aware API | ✅ | `/query` + `/domains` endpoints |
| 16-17: Ingestion + E2E | ✅ | 10 files ingested, API tested |
| 18-20: Exam Prep | ✅ | 5 articles ingested, isolation verified |
| 21-25: Benchmarks | ✅ | 18 QA pairs per domain, full runs + Recall@5/MRR, `benchmark-results/` |
| 26-29: Regression Tests | ✅ | 120/120 passing; automation scripts added (29) |
| 30-31: README & Docs | ✅ | README rewritten (dual-domain), `docs/ARCHITECTURE.md` created |
| 32-34: Deployment Prep | ⚠️ | Env vars done (34) + hardcoded paths fixed; Docker/volumes need verification (32-33) |
| 35-37: Deployment | ⏸️ | Pending — needs human decision on provider |
| 38-39: Final E2E + Report | ⏸️ | Pending — depends on deployment |

---

## Human Actions Required

1. **Set OpenRouter API key** — for Agent TUI live testing
2. **Choose deployment provider** — Railway or Render (Phase 35)
3. **Decide on path strategy** — replace hardcoded `/Users/pallav/` paths or use env vars (Phase 34)

---

## Next Steps (Priority Order)

1. **Phase 30-31**: README rewrite + architecture docs (can be done now)
2. **Phase 32-34**: Deployment prep — Dockerfile audit, storage, env vars (can be done now)
3. **Phase 35-37**: Deployment — needs human input on provider
4. **Phase 38-39**: Final E2E + completion report
