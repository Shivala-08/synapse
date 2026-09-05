# Synapse Architecture — One Engine, Many Domains

**Status:** Current as of September 2026 (dual-domain, DB-backed graph, Next.js frontend).

This document explains how Synapse serves multiple independent knowledge
domains — a Second Brain vault and an Exam Prep corpus — from one codebase.
The core rule: **domain configuration changes source, entity types, link
syntax, storage namespace, and chunk settings. It never changes the
retrieval architecture.**

---

## 1. The big picture

```
                         Domain Profile
                              │
              ┌───────────────┴───────────────┐
              │                               │
        Second Brain                      Exam Prep
              │                               │
        Markdown wiki                    PDF/DOCX/PPTX/TXT
        [[wikilinks]]                    study material
              │                               │
              └───────────────┬───────────────┘
                              │
                        Shared Pipeline
                              │
                  ┌───────────┼───────────┐
                  │           │           │
                Vector       BM25        Graph
                (ChromaDB)  (per-domain) (DB-backed)
                  │           │           │
                  └───────────┼───────────┘
                              │
                     CrossEncoder Rerank
                              │
                       Adaptive LLM Router
                              │
                            Answer
```

The workspace keeps three separate components:

| Component | Path | Role |
|---|---|---|
| Synapse | `Rag-eco-hackathon/` | Shared retrieval engine (this repo) |
| Second Brain | `second-brain/` | Obsidian vault — human-readable source of truth |
| Agent TUI | `second-brain-agent/` | AI librarian: compiles `raw/` → `wiki/` |

**Data flow (Second Brain):**

```
human material → raw/ → Agent compilation → wiki/*.md → re-sync → Synapse → retrieval
```

The wiki is authoritative. Synapse's index is derived and re-ingestable.
Never edit Synapse's stored chunks to "fix" knowledge — fix the wiki, re-sync.

---

## 2. Domain profiles: the only per-domain surface

Each domain is a single YAML file in `domains/`. Loading it
(`src/config.py::load_domain_profile`) yields a `DomainProfile` pydantic
model that threads through every layer.

```yaml
# domains/second_brain.yaml (abridged)
domain_id: second_brain
source_path: "second-brain/wiki"        # relative to workspace root
collection_name: "second_brain_vectors" # vector namespace
graph_file: "data/second_brain_knowledge_graph.json"
entity_types: [Project, TechStack, ...] # what the extractor looks for
link_syntax: wikilink                   # [[Note]] → LINKS_TO edges
chunk_size: 512
```

### 2.1 Source path resolution

`load_domain_profile` resolves `source_path` in this order:

1. `os.environ[<DOMAIN_ID>_SOURCE_PATH]` — e.g. `SECOND_BRAIN_SOURCE_PATH`
   (production mounts).
2. The YAML value after `$VAR` / `${VAR}` expansion.
3. Relative paths resolve against the workspace root: `ADHD_CURE_ROOT` env
   var, or the repo's parent directory by default.

This removed the hardcoded `/Users/<user>/Desktop/Adhd-cure/...` paths while
staying backward compatible (absolute paths pass through untouched).

### 2.2 What a domain owns

| Layer | Per-domain construct | Mechanism |
|---|---|---|
| Vector | collection `second_brain_vectors` vs `exam_prep_vectors` | `chroma_store.py` names the collection from the profile |
| BM25 | separate `BM25Index` instance | `bm25_index.py` keeps `_bm25_indexes[domain_id]` |
| Graph | `domain_id` column on node/edge rows | `knowledge_graph.py` scopes every read/write |
| Registry | `data/documents_<domain>.json` | `ingest.py` per-domain registry |
| Chunking | size/overlap from profile | `ingest.py` passes them to `chunk_text` |
| Entities | profile `entity_types` guides extraction | `extractor.py` uses profile-aware regex/spaCy |
| Links | `wikilink` vs `none` | gates `[[Note]]` parsing → `LINKS_TO` edges |

The shared pipeline (`parser.py`, `chunker.py`, `embedder.py`, `llm.py`)
never sees domain IDs — it processes whatever text it is given.

---

## 3. Ingestion pipeline

```
file → parser (txt/pdf/docx/csv/md/pptx) → chunker → embedder
                                              ↓
                                    extractor (spaCy + regex + wikilinks)
                                              ↓
                        ChromaDB collection  +  knowledge graph  +  BM25 rebuild
                                              ↓
                               relational DB (documents, chunks, graph, cache)
```

Key behaviors:

- **Per-chunk entity extraction.** `entity_ids` JSON lands in each chunk's
  metadata so retrieval can seed graph traversal from the chunks it finds.
- **Wikilink pass** (gated on `link_syntax: wikilink`). `[[Note]]` targets
  become `Note` nodes with `LINKS_TO` edges from the source note — on top of
  automatic entity edges, not instead of them.
- **Non-destructive sync.** `scripts/sync_second_brain.py` (and
  `POST /ingest/re-sync`) scan the source path and ingest only documents
  missing from the registry. Existing documents are never overwritten or
  deleted.
- **BM25 rebuild** happens after each document so the domain index reflects
  the current collection.

---

## 4. Retrieval pipeline

```
query
  → embed + BM25 scores (domain-scoped)
  → hybrid fusion (α·BM25 + (1-α)·vector) → top 8 candidates
  → CrossEncoder re-rank (keyword boost for prose docs) → top 3 chunks
  → entity extraction (query + chunk metadata) → 1-hop graph traversal
  → prompt assembly (chunks + graph relations + confidence guide)
  → adaptive LLM router (fast / deep / smart fallback)
  → answer + sources + confidence + per-stage trace
```

### 4.1 Routing

`classify_query_complexity` gates thinking mode:

| Mode | Model | Thinking | Use case |
|---|---|---|---|
| `fast` | `meta/llama-3.2-11b-vision-instruct` | off | lookups, direct questions |
| `deep` | `nvidia/nemotron-3-ultra-550b-a55b` | on (budget 1024) | explicit comparison/synthesis |
| `auto` | classifier picks | heuristic | default |
| fallback | Smart Context | — | no LLM reachable — formats retrieved chunks |

The 11B vision-instruct model replaced the deprecated `llama-3.1-8b-instruct`
(2026-08-26 EOL). The 550B model's ~40s first token means deep mode is only
selected on genuine synthesis signals (comparison language, long queries) —
routine lookups that happened to span two documents no longer trigger it.

### 4.2 Semantic cache

Two tiers: an in-memory rolling list (cosine ≥ 0.95, FIFO eviction) and a
relational table. Only `auto` mode reads the cache; hits are labeled
`(Semantic Cache)` in `model_used` and the trace `cache: hit`.

### 4.3 Trace

Every response carries `trace` (cache, hybrid, reranker, candidates,
chunks_used, graph_entities, graph_relations, model, routing_mode, latency)
rendered by the frontend as a Query → Cache → Retrieve → Rerank → Graph →
LLM → Answer step indicator. The streaming endpoint additionally checks the
cache up front and emits tokens via SSE.

---

## 5. Knowledge graph

- **Persistence:** relational DB (`graph_nodes`, `graph_edges` tables) with a
  `domain_id` column — no JSON files on disk. `IndustrialKnowledgeGraph` syncs
  DB → NetworkX at construction and writes through on every mutation.
- **Domain scoping:** every query (`_sync_from_db`, `get_entities_by_type`,
  etc.) filters by `domain_id` when a profile is present. `clear()` deletes
  only the active domain's rows.
- **Entity types:** industrial schema (equipment, regulation, permit, …) plus
  a generic path: any unhandled category (e.g. `DatabaseConcept`,
  `SQLCommand`) becomes nodes of that type, and co-occurring entities in a
  document get `co_occurs_with` edges — this is what makes the Exam Prep
  graph connected.
- **Wikilinks:** `add_wikilink_entities` creates `Note` nodes + `LINKS_TO`
  edges (Second Brain only).
- **Mastery / Roadmap:** `/mastery` computes per-entity-type graph coverage
  (share of entities with degree > 0) as an estimated mastery score;
  `/roadmap/plan` allocates daily hours proportional to inverse mastery so
  weakest topics get the most time.

---

## 6. API layer (`src/main.py`)

- Every domain-aware endpoint accepts `domain_id` (query param or body
  field) and resolves the profile up front. Explicit domain always wins;
  omitting it falls back to the first configured domain.
- **Admin guard:** `ADMIN_API_KEY` via `X-API-Key` protects destructive
  endpoints (`/ingest/*`, `/benchmark/run`, `/debug/search`). Unset = open
  (local dev), with a startup warning.
- **Event-loop hygiene:** streaming queries pull retrieval, embedding, and
  token iteration through `run_in_threadpool` so synchronous CPU/IO work
  never blocks the SSE stream.
- **Telemetry:** `TelemetryLog` rows record retrieval/generation latency,
  model, cache hit, and errors per query.

---

## 7. Frontend (`web/`, Next.js App Router)

Domain-routed: `/[domain]/query`, `/[domain]/graph`, `/[domain]/library`,
plus `/[domain]/revision` and `/[domain]/roadmap` for `exam_prep` only.

| Page | Backend | Purpose |
|---|---|---|
| Query console | `/query/stream` | SSE chat, routing selector, pipeline animation, evidence panel |
| Graph explorer | `/graph`, `/graph/node`, `/graph/path` | Force-graph visualization, node search, path finder |
| Library | `/documents`, `/ingest/upload`, `/ingest/re-sync` | Source list, drag-drop upload, vault sync |
| Revision | `/mastery` | Mastery ring + weakest-first topic bars (local activity log) |
| Roadmap | `/roadmap/plan` | Day-by-day study timeline, hover tooltips, shareable `?exam=` links |

The `Rail` sidebar lists all domains (status LEDs probe `/documents?domain_id=`)
and swaps the whole app context via `DomainContext` (`second_brain` →
`/second-brain/...` segments).

---

## 8. Testing & benchmarking

- **120 pytest tests** (`tests/`): domain isolation (13), extractor (52),
  knowledge graph (25), query engine (14), LLM routing (10), chunker (5),
  ChromaDB (1). Run: `PYTHONPATH=. pytest tests/ -q`.
- **Benchmark harness** (`run_benchmark_now.py --domain <id>`): 18 grounded
  QA pairs per domain (6 direct lookup / 6 cross-reference / 6 synthesis),
  scoring via semantic similarity ≥ 0.55 AND expected source in top-3 context.
  Emits accuracy, avg latency, **Recall@5**, **MRR**, and retrieval success
  (computed over the top-8 re-ranked candidate list) to
  `benchmark-results/` + `summary.md`.
- **CI:** GitHub Actions (`python-ci.yml`) runs the suite on push.

---

## 9. Operations

- **Start:** `./start.sh` (backend :8000, frontend :3000). `stop.sh` to kill.
- **Vault sync:** `scripts/compile-and-ingest-second-brain.sh` runs
  audit → additive sync → validation. Agent compilation stays an interactive,
  approval-gated step (`npm start` in `second-brain-agent/`).
- **Deployment:** stateful environment (Railway/Render). Mount a volume at
  `/app/data` — the Dockerfile seeds `/app/data_seed` on first boot so
  pre-built ChromaDB collections and the SQLite DB survive restarts.
  Vercel runs only the frontend.
- **Env:** full annotated template in `.env.example` (paths, NIM keys,
  admin key, CORS, feature flags).

---

## 10. Known limitations (verified)

- Answer accuracy lags retrieval quality: Recall@5 is 100% but synthesis
  accuracy is lower — the fast model misses abstract "across these documents"
  questions. Deep routing covers some, at 40s+ latency.
- The vault's wikilinks don't all resolve under strict Obsidian semantics
  (e.g. `[[jarvis-memory]]` vs actual note `memory-system.md`); the strict
  audit in `scripts/audit_wiki.py` reports them.
- Registry keys documents by filename, so `_index.md` files from different
  topic folders collide (only one survives per sync).
- Benchmark metrics are answer-text similarity based; there is no
  human-validated reference answer set beyond the QA pairs.