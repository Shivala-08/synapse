# ADHD-CURE Build Manual — Phase Results

**Last Updated:** Phases 25, 29, 30, 31, 34 Complete (Benchmarks, Automation, README, Architecture, Env)
**Test Status:** 120/120 passing ✅
**Benchmark Results:** Second Brain 66.7% (12/18), Study Materials 77.8% (14/18) — full 18-question runs, Recall@5 100% both
**Overall:** 23/32 phases complete, 5 blocked (27, 35-39), 4 pending (32, 33, 36, 37, 38)

---

## Phase 0: Workspace Discovery ✅ COMPLETE

**What was done:**
- Inspected all three projects (Synapse/Rag-eco-hackathon, Second Brain, Second Brain Agent)
- Catalogued existing functionality, missing features, and known errors
- Created `PROJECT_STATE.md` with full architecture documentation

**Results:**
- Synapse: FastAPI + Streamlit RAG engine with vector/graph/BM25 retrieval
- Second Brain: Obsidian vault with raw material and empty wiki
- Agent TUI: TypeScript CLI with OpenRouter integration, approval bug present
- BM25 identified as NOT domain-aware (critical bug)
- Domain profiles exist but with placeholder paths

---

## Phase 1: Agent TUI Approval Bug ✅ COMPLETE

**What was done:**
- Inspected `@openrouter/agent` SDK v0.11.0 types
- Identified `StateAccessor` interface requirement for approval gates
- Created `second-brain-agent/src/state.ts` — file-backed StateAccessor
- Updated `second-brain-agent/src/agent.ts` — passes state to `callModel()`
- Updated `second-brain-agent/src/cli.ts` — handles approval/rejection flow

**Results:**
- TypeScript compiles cleanly (`npx tsc --noEmit` passes)
- Approval workflow: agent requests write → CLI shows approval prompt → user approves → tool executes
- Vault sandboxing preserved (assertInsideVault still enforced)
- State persisted to disk for multi-turn conversations

---

## Phase 2: Second Brain Compilation ✅ COMPLETE

**What was done:**
- Read all 4 raw material files from `second-brain/raw/`
- Created topic folders: `campus-hub/`, `jarvis/`, `synapse/`
- Compiled 6 wiki articles with [[wikilinks]] cross-references
- Created topic `_index.md` files for each topic
- Updated `_master-index.md` with all topics

**Results:**
- 10 markdown files in `wiki/` (6 articles + 3 indexes + master index)
- 7 wikilinks connecting articles across topics
- All articles have `## Key Takeaways` sections
- Raw material preserved untouched in `raw/`

---

## Phase 3: Second Brain Vault Audit ✅ COMPLETE

**What was done:**
- Checked for missing `_index.md` files: NONE
- Checked for broken wikilinks: NONE
- Checked for empty articles: NONE
- Checked for missing Key Takeaways: NONE
- Checked for orphaned articles: NONE
- Created `second-brain/output/wiki-audit.md`

**Results:**
- All 3 topic folders have `_index.md`
- All 6 articles referenced from topic indexes
- All wikilinks resolve to existing articles
- Raw material coverage: 4/4 files compiled

---

## Phase 4-7: Synapse Domain Architecture & Profiles ✅ COMPLETE

**What was done:**
- Updated `domains/second_brain.yaml` with real source path
- Updated `domains/exam_prep.yaml` with placeholder path (user must configure)
- Verified `load_domain_profile()` works for both domains
- Verified `list_domains()` returns both domains

**Results:**
- Second Brain profile: `second_brain_vectors` collection, wikilink syntax, 512 chunk size
- Exam Prep profile: `exam_prep_vectors` collection, no links, 1024 chunk size
- Domain profile loader tested and working

---

## Phase 8-12: Storage Isolation ✅ COMPLETE

**What was done:**
- Vector isolation: Already domain-aware via DomainProfile in `chroma_store.py` ✅
- Graph isolation: Already domain-aware via DomainProfile in `knowledge_graph.py` ✅
- **Fixed BM25 domain isolation**: Rewrote `bm25_index.py` with domain-scoped indexes
- Wikilink extraction: Already implemented in `extractor.py` ✅
- LINKS_TO edges: Already implemented in `knowledge_graph.py` ✅
- Updated `query_engine.py` to use domain-scoped BM25
- Updated `ingest.py` to rebuild domain-specific BM25 after ingestion
- Added `.md` support to `parser.py`

**Results:**
- BM25 now uses per-domain indexes (`_bm25_indexes` dict keyed by domain_id)
- Cross-domain contamination prevented at vector, graph, and BM25 layers
- Markdown files parseable as text documents
- All modules import cleanly

---

## Phase 13-15: Domain-Aware Query Engine, UI, API ✅ COMPLETE

**What was done:**
- Added `domain_id` parameter to `QueryRequest` model
- Updated `/query` endpoint to resolve domain profile from `domain_id`
- Updated `/query/stream` endpoint with domain support
- Added `/domains` endpoint listing available domain profiles
- Added `domain` field to `QueryResponse` model
- Verified Streamlit UI already has domain selector in sidebar

**Results:**
- API: `POST /query` accepts `domain_id` parameter, returns resolved domain in response
- API: `GET /domains` returns available domains with metadata
- UI: Domain selector in sidebar switches collections, BM25, graph, and queries
- FastAPI app compiles and imports cleanly

---

## Phase 16-17: Second Brain Ingestion & End-to-End Test ✅ COMPLETE

**What was done:**
- Ingested all 10 wiki markdown files into `second_brain_vectors` collection
- Created embeddings via SentenceTransformer (all-MiniLM-L6-v2)
- Built domain-scoped BM25 index for second_brain
- Ingested into relational database for persistence

**Results:**
- 10 files ingested successfully
- 12 chunks created (some files split into multiple chunks)
- Collection `second_brain_vectors` populated
- BM25 index built for second_brain domain
- Note: Entity extraction found 0 entities (wiki content lacks industrial tags — expected)

**API Verification:**
- Health endpoint: `GET /health` returns `"ok"`
- Query `second_brain` domain: Returns real results from ingested wiki
- Query `exam_prep` domain: Correctly returns "No documents indexed yet"
- Default query (no domain): Uses first available domain
- All 107 pytest tests pass

---

## Phase 18-20: Exam Prep & Cross-Domain Isolation ✅ COMPLETE

**What was done:**
- Created 5 synthetic exam prep articles covering ADHD/neuroscience:
  - `adhd_fundamentals.md` — DSM-5 criteria, subtypes (1.8 KB)
  - `neurotransmitters.md` — Dopamine, NE, serotonin, GABA (2.5 KB)
  - `adhd_treatment.md` — Stimulants, non-stimulants, behavioral (2.8 KB)
  - `brain_anatomy.md` — PFC, basal ganglia, DMN (2.5 KB)
  - `executive_function.md` — Working memory, inhibitory control (4.5 KB)
- Updated `domains/exam_prep.yaml` with correct schema and source path
- Ingested all 5 files into `exam_prep_vectors` collection
- Verified cross-domain isolation:
  - Jarvis content does NOT leak into exam_prep domain ✅
  - Dopamine content does NOT leak into second_brain domain ✅
  - Each domain has its own vector store collection ✅
  - Each domain has its own BM25 index ✅

**Results:**
- `exam_prep_vectors` collection: 5 chunks
- `second_brain_vectors` collection: 10 chunks
- Cross-domain queries return correct domain-scoped results
- No cross-contamination detected

---

## Phase 21-25: Benchmarks ✅ COMPLETE

**What was done:**
- Created `data/benchmarks/qa_pairs_second_brain.json` — 18 questions (6 DL + 6 XR + 6 Synthesis)
- Created `data/benchmarks/qa_pairs_exam_prep.json` — 18 questions (6 DL + 6 XR + 6 Synthesis)
- Created `run_benchmark_now.py` — CLI harness with `--domain` flag
- Updated `/benchmark/run` endpoint to accept `domain` parameter
- All questions grounded in actual source material
- Fixed deprecated LLM model (`meta/llama-3.1-8b-instruct` → `meta/llama-3.2-11b-vision-instruct`)
- **Phase 25 output:** harness now computes Recall@5, MRR, and retrieval success over the top-8 candidate list; results written to `benchmark-results/<domain>.json` + `benchmark-results/summary.md`
- **Graph fix:** both domain knowledge graphs were empty (0 nodes); `populate_domain_graphs.py` rebuilt them before the full runs so the whole pipeline (including graph retrieval) is measured

**Benchmark Results (Verified — full 18-question runs, Sept 2026):**
| Domain | Accuracy | Avg Latency | Recall@5 | MRR | Retrieval Success |
|--------|----------|-------------|----------|-----|-------------------|
| Second Brain | 66.7% (12/18) | 12.8s | 100.0% | 0.833 | 100.0% |
| Study Materials | 77.8% (14/18) | 15.3s | 100.0% | 1.000 | 100.0% |

By category (second_brain / exam_prep): direct lookup **83.3% / 83.3%**, cross-reference **66.7% / 66.7%**, synthesis **50.0% / 83.3%**.

> Earlier 6-question runs (83.3% / 66.7%) covered direct lookup only; the full 18-question numbers above are the current measured state.

**QA Pair Categories:**
| Type | Second Brain | Study Materials |
|------|-------------|------------------|
| Direct Lookup | 6 | 6 |
| Cross-Reference | 6 | 6 |
| Synthesis | 6 | 6 |
| **Total** | **18** | **18** |

**Benchmark Commands:**
```bash
PYTHONPATH=. python run_benchmark_now.py --domain second_brain
PYTHONPATH=. python run_benchmark_now.py --domain exam_prep
PYTHONPATH=. python run_benchmark_now.py --list
```

---

## Phase 26-29: Regression Tests ✅ COMPLETE

**What exists:**
- 8 test files in `Rag-eco-hackathon/tests/`
- Tests for chromadb, chunker, llm, extractor, query_engine, knowledge_graph
- **New: `test_domain_isolation.py`** — 13 tests for domain switching and BM25 isolation
- **120/120 tests passing** ✅

**Test Files:**
| File | Tests | Status |
|------|-------|--------|
| test_chromadb.py | 1 | ✅ |
| test_chunker.py | 5 | ✅ |
| test_extractor.py | 52 | ✅ |
| test_knowledge_graph.py | 25 | ✅ |
| test_llm.py | 10 | ✅ |
| test_query_engine.py | 14 | ✅ |
| test_domain_isolation.py | 13 | ✅ |
| **Total** | **120** | **All passing** |

---

## Phase 29: Optional Automation ✅ COMPLETE

**What was done:**
- Created `scripts/compile-and-ingest-second-brain.sh` — orchestration: audit → additive sync → validation
- Created `scripts/audit_wiki.py` — strict vault audit (missing indexes, empty articles, missing Key Takeaways, broken wikilinks resolved against actual notes)
- Created `scripts/sync_second_brain.py` — non-destructive re-sync (only adds missing documents)
- Agent compilation step preserved as interactive + approval-gated (never automated)

**Verified:**
- Audit runs against the vault (found 7 genuinely dangling wikilinks the old lenient audit missed — reported, not auto-fixed)
- Sync runs: 0 added, 10 skipped (already indexed), 0 errors; prints validation counts

---

## Phase 30-31: README & Architecture Docs ✅ COMPLETE

**What was done:**
- Rewrote `Rag-eco-hackathon/README.md` — leads with dual-domain proposition + benchmark table, covers architecture, domain profiles, wikilink graph, hybrid retrieval, "why Synapse", install/config/run/benchmark/deploy
- Created `docs/ARCHITECTURE.md` — "one engine, many domains": domain profiles as the only per-domain surface, ingestion/retrieval pipelines, graph + mastery/roadmap, API, frontend, ops, verified limitations

---

## Phase 32-34: Deployment Preparation ⚠️ PARTIAL (34 done)

**Done (Phase 34 — env vars):**
- `config.py` now resolves source paths: `<DOMAIN>_SOURCE_PATH` env override → `$VAR` expansion → workspace root (`ADHD_CURE_ROOT`, defaults to repo parent)
- Removed hardcoded `/Users/pallav/Desktop/Adhd-cure/` paths from both domain YAMLs (portable relative paths)
- `.env.example` fully annotated: paths, NIM keys, admin key, CORS, feature flags

**Remaining (32-33):**
- Verify Dockerfile build + persistent volume mount for `data/` (chroma_db, synapse.db, registries)
- Run smoke test of start.sh locally

---

## Phase 35-37: Deployment & Smoke Tests ⏸️ PENDING (Needs human input)

**Human action needed:**
- Choose deployment provider (Railway or Render)
- Provide deployment credentials
- Decide on source-path strategy for production

**What needs to be done:**
- Deploy to chosen provider
- Test /health endpoint
- Test both domains (Second Brain + Exam Prep)
- Verify domain switching in UI
- Test restart persistence

---

## Phase 38-39: Final E2E Test & Completion Report ⏸️ PENDING

**What needs to be done:**
- Full end-to-end test: raw note → Agent → wiki → Synapse → retrieval → answer
- Cross-domain isolation final verification
- Create PROJECT_COMPLETION_REPORT.md with final status

---

## Summary of All Changes

### Files Created
| File | Purpose |
|---|---|
| `PROJECT_STATE.md` | Workspace discovery document |
| `PHASE_RESULTS.md` | This file — phase completion results |
| `second-brain-agent/src/state.ts` | File-backed StateAccessor for approval |
| `run_benchmark_now.py` | CLI benchmark harness with `--domain` flag |
| `data/benchmarks/qa_pairs_second_brain.json` | 18 QA pairs for Second Brain domain |
| `data/benchmarks/qa_pairs_exam_prep.json` | 18 QA pairs for Exam Prep domain |
| `second-brain/wiki/campus-hub/_index.md` | CampusHub topic index |
| `second-brain/wiki/campus-hub/campushub-fix-instructions.md` | CampusHub article |
| `second-brain/wiki/jarvis/_index.md` | Jarvis topic index |
| `second-brain/wiki/jarvis/cloud-model-layer.md` | Jarvis cloud models article |
| `second-brain/wiki/jarvis/memory-system.md` | Jarvis memory article |
| `second-brain/wiki/jarvis/graph-orchestrator.md` | Jarvis graph orchestrator article |
| `second-brain/wiki/jarvis/coding-agent.md` | Jarvis coding agent article |
| `second-brain/wiki/synapse/_index.md` | Synapse topic index |
| `second-brain/wiki/synapse/architecture.md` | Synapse architecture article |
| `second-brain/output/wiki-audit.md` | Vault audit report |
| `Rag-eco-hackathon/exam_prep_material/*.md` | 5 exam prep articles |
| `Rag-eco-hackathon/tests/test_domain_isolation.py` | Domain isolation tests |

### Files Modified
| File | Changes |
|---|---|
| `second-brain-agent/src/agent.ts` | Added StateAccessor support |
| `second-brain-agent/src/cli.ts` | Added approval workflow handling |
| `Rag-eco-hackathon/src/pipeline/bm25_index.py` | Made BM25 domain-aware |
| `Rag-eco-hackathon/src/pipeline/query_engine.py` | Domain-scoped BM25 usage |
| `Rag-eco-hackathon/src/pipeline/ingest.py` | Domain-scoped BM25 rebuild |
| `Rag-eco-hackathon/src/pipeline/parser.py` | Added .md and .pptx file support |
| `Rag-eco-hackathon/src/main.py` | Added domain_id to query endpoints, /domains endpoint, domain field in response |
| `Rag-eco-hackathon/domains/second_brain.yaml` | Real source path |
| `Rag-eco-hackathon/domains/exam_prep.yaml` | Correct schema with real paths + pptx support |

---

## Human Actions Required

1. **OpenRouter API key** — Set in `.env` for Agent TUI live testing
2. **Deployment provider choice** — Railway or Render (Phase 35)
3. **Path strategy** — Confirm whether to replace hardcoded paths with env vars

---

## Next Steps (Priority Order)

1. **Phase 30-31**: README rewrite + architecture docs (can be done now)
2. **Phase 32-34**: Deployment prep — Dockerfile audit, storage, env vars (can be done now)
3. **Phase 35-37**: Deployment — needs human input on provider
4. **Phase 38-39**: Final E2E + completion report
