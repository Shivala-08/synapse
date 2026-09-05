# Synapse — One Hybrid Retrieval Engine, Many Domains

**One hybrid retrieval engine, two live personal domains — a Second Brain
built on the Obsidian + Claude Code pattern, and an Exam Prep assistant over
real coursework. Swap the domain config, not the code.**

Synapse is a graph-augmented RAG engine that ingests heterogeneous documents
and answers questions with cited, confidence-scored responses by merging
semantic vector search, BM25 keyword search, and a knowledge graph. The same
pipeline serves every domain — only configuration, source data, entity types,
link syntax, and storage namespaces change.

---

## Benchmark Results

Full 18-question ground-truth runs per domain (fast routing model,
`meta/llama-3.2-11b-vision-instruct`, September 2026):

| Domain | Questions | Accuracy | Avg Latency | Recall@5 | MRR | Retrieval Success |
|---|---:|---:|---:|---:|---:|---:|
| second_brain | 18 | **66.7%** | 12.8s | 100.0% | 0.833 | 100.0% |
| exam_prep | 18 | **77.8%** | 15.3s | 100.0% | 1.000 | 100.0% |

By category (second_brain / exam_prep): direct lookup **83.3% / 83.3%**,
cross-reference **66.7% / 66.7%**, synthesis **50.0% / 83.3%**.

Retrieval always finds the right source documents (Recall@5 = 100%); accuracy
gaps are answer-generation misses, mostly on synthesis questions. Details and
per-question traces: `benchmark-results/summary.md`.

---

## Architecture

```
                         Domain Profile
                              │
              ┌───────────────┴───────────────┐
              │                               │
        Second Brain                      Exam Prep
              │                               │
        Markdown wiki                    PDF/DOCX/PPTX
        ([[wikilinks]])                   study material
              │                               │
              └───────────────┬───────────────┘
                              │
                        Shared Pipeline
                              │
                  ┌───────────┼───────────┐
                  │           │           │
                Vector       BM25        Graph
                  │           │           │
                  └───────────┼───────────┘
                              │
                     CrossEncoder Rerank
                              │
                       Adaptive LLM Router
                              │
                            Answer
```

The workspace is three separate components that stay separate:

```
adhd-cure/
├── Rag-eco-hackathon/     Synapse — the shared RAG engine (this repo)
├── second-brain/          Obsidian vault — the human-readable source of truth
└── second-brain-agent/    AI librarian — compiles raw/ → wiki/ (TypeScript CLI)
```

**Data flow:** human material → `second-brain/raw/` → Agent compilation →
`second-brain/wiki/*.md` → Synapse re-sync → retrieval. Synapse is never the
authoritative store — the wiki is. When indexes go stale, re-ingest.

---

## Repository Structure

```
├── data/                       # Ingested and generated data
│   ├── chroma_db/              # ChromaDB vector stores (per domain collection)
│   ├── benchmarks/             # QA pairs + per-run results
│   ├── synapse.db              # Relational DB (documents, chunks, graph, cache)
│   └── documents_<domain>.json # Per-domain ingestion registries
│
├── domains/                    # Domain profiles — the ONLY per-domain config
│   ├── second_brain.yaml
│   └── exam_prep.yaml
│
├── src/                        # System source code
│   ├── main.py                 # FastAPI application and endpoints
│   ├── config.py               # Settings + DomainProfile loader
│   ├── pipeline/               # parser, chunker, embedder, extractor, ingest,
│   │                           #   query_engine, bm25_index, llm, compliance
│   ├── storage/                # chroma_store.py (domain-aware collections)
│   ├── graph/                  # knowledge_graph.py (domain-aware, DB-backed)
│   └── database/               # SQLAlchemy session + models
│
├── scripts/
│   ├── compile-and-ingest-second-brain.sh   # audit → sync → validate
│   ├── audit_wiki.py                        # vault integrity check
│   ├── sync_second_brain.py                 # additive vault → Synapse sync
│   └── populate_domain_graphs.py            # rebuild domain graphs from chunks
│
├── web/                        # Next.js frontend (domain-routed)
├── tests/                      # 120 tests
├── run_benchmark_now.py        # CLI benchmark harness
├── Dockerfile / start.sh / stop.sh
└── requirements.txt
```

---

## Domain Profiles

Each domain is fully described by one YAML file. Nothing in the core pipeline
knows about any specific domain.

| Setting | second_brain | exam_prep |
|---|---|---|
| `source_path` | `second-brain/wiki` | `second-brain/raw` |
| `source_types` | `.md` | `.pdf .docx .txt .pptx .md` |
| `collection_name` | `second_brain_vectors` | `exam_prep_vectors` |
| `graph_file` | `data/second_brain_knowledge_graph.json` | `data/exam_prep_knowledge_graph.json` |
| `entity_types` | Project, TechStack, BugFix, APIIntegration, Decision | DatabaseConcept, SQLCommand, ProgrammingLanguage, Framework, APIEndpoint |
| `link_syntax` | `wikilink` | `none` |
| `chunk_size` | 512 | 1024 |

Source paths are resolved as: `<DOMAIN_ID>_SOURCE_PATH` env var (if set) →
YAML value with `$VAR` expansion → relative paths resolved against the
workspace root (`ADHD_CURE_ROOT`, defaulting to this repo's parent).

---

## Second Brain (wiki domain)

- Vault lives outside this repo in `second-brain/` (`wiki/`, `raw/`, `output/`).
- The Agent TUI compiles raw material into topic folders with Obsidian
  `[[wikilinks]]` — approval-gated writes, sandboxed to the vault.
- **Wikilinks become graph edges.** `[[React]]` inside a note creates a
  `LINKS_TO` relationship during ingestion, alongside automatic spaCy/regex
  entity extraction. Neither Obsidian nor a plain RAG stack does this alone.
- Re-sync from the Library page (or `scripts/sync_second_brain.py`) picks up
  new notes without touching existing documents.

## Exam Prep (study materials domain)

- Drop course files (PDF, DOCX, PPTX, TXT) into `second-brain/raw/`, re-sync.
  PPTX parsing covers slides, tables, and speaker notes.
- Query the corpus, then use the **Revision** dashboard (topic mastery
  estimated from knowledge-graph coverage, weakest first) and **Roadmap**
  (a day-by-day study plan allocating hours to your weakest topics).

---

## Hybrid Retrieval

1. Query embedded + BM25 scores computed against the domain's index.
2. Hybrid fusion (vector + BM25) → top 8 candidates → CrossEncoder re-rank
   (`ms-marco-MiniLM-L-6-v2`) → top 3 chunks into context.
3. Entities extracted from the query + chunks drive a 1-hop graph traversal
   that pulls in related entities and relations.
4. A complexity classifier picks the LLM path: simple lookups → fast
   `llama-3.2-11b-vision-instruct`; complex synthesis → deep
   `nemotron-550b` with thinking mode; no LLM available → "Smart Context"
   fallback that formats retrieved chunks directly.
5. Semantic cache (in-memory + relational) answers near-duplicate questions
   instantly. Every response carries sources, confidence, and a per-stage
   trace rendered as a Query → Cache → Retrieve → Rerank → Graph → LLM →
   Answer indicator in the UI.

## Why Synapse instead of only Obsidian / Claude Code?

Obsidian is a great writing surface but has no retrieval quality signals.
Synapse adds: hybrid search with cross-encoder re-ranking, an entity knowledge
graph with wikilink edges, confidence scores, per-stage traces, benchmarkable
Recall@5/MRR/accuracy, adaptive model routing, and a graph explorer. The
Second Brain stays the source of truth; Synapse makes it *searchable*.

---

## Quick Start

### Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+** (for the Next.js frontend)
- **Optional:** NVIDIA NIM API key ([free tier](https://build.nvidia.com/))
  or [Ollama](https://ollama.com/) for local LLM answers

### 1. Install

```bash
git clone <your-repo-url>
cd synapse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cd web && npm install && cd ..
```

### 2. Configure

```bash
cp .env.example .env
# Add NVIDIA_API_KEY_1 (or install Ollama). Without either, answers use the
# Smart Context fallback (formatted retrieved chunks, no LLM).
```

### 3. Launch

```bash
./start.sh
```

- **Backend:** http://localhost:8000 (docs at `/docs`)
- **Frontend:** http://localhost:3000

### 4. Ingest a domain

Upload files from the Library page, or re-sync from the source folder:

```bash
curl -X POST "http://localhost:8000/ingest/re-sync?domain_id=second_brain"
curl -X POST "http://localhost:8000/ingest/re-sync?domain_id=exam_prep"
```

### 5. Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a candidate key?", "domain_id": "exam_prep"}'
```

---

## API Reference

All endpoints documented at http://localhost:8000/docs (Swagger UI).

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/llm/status` | GET | LLM availability |
| `/query` | POST | Non-streaming RAG query (accepts `domain_id`, `routing_mode`) |
| `/query/stream` | POST | SSE streaming RAG query |
| `/domains` | GET | List available domain profiles |
| `/documents` | GET | List ingested documents per domain |
| `/ingest/upload` | POST | Upload and ingest files (Admin) |
| `/ingest/re-sync` | POST | Scan a domain's source path, ingest new files (Admin) |
| `/graph`, `/graph/search`, `/graph/path`, `/graph/stats` | GET | Knowledge graph exploration |
| `/mastery` | GET | Per-topic mastery from graph coverage |
| `/roadmap/plan` | GET | Day-by-day study plan (weakest topics first) |
| `/benchmark/run` | GET | Run ground-truth benchmark per domain (Admin) |
| `/feedback` | POST | Log thumbs up/down feedback |

---

## Configuration

All settings in `src/config.py`, loaded from `.env` (full annotated template:
`.env.example`).

| Setting | Default | Description |
|---|---|---|
| `ADHD_CURE_ROOT` | repo parent | Workspace root for resolving relative domain source paths |
| `<DOMAIN>_SOURCE_PATH` | — | Per-domain source path override (e.g. `SECOND_BRAIN_SOURCE_PATH`) |
| `ADMIN_API_KEY` | `""` | Guards destructive endpoints (`X-API-Key` header) |
| `REQUIRE_ADMIN_KEY` | `false` | Abort startup without an admin key |
| `CORS_ORIGINS` | allow all | Comma-separated allowed origins |
| `NVIDIA_API_KEY_1..10` | `""` | NVIDIA NIM keys, tried in order |
| `NVIDIA_NIM_API_KEYS` | `""` | Comma-separated key pool alternative |
| `HF_TOKEN` | `""` | Hugging Face token for embedding API fallback |
| `chunk_size` | `1024` | Tokens per chunk (overridable per domain) |
| `top_k` | `50` | Default chunks retrieved |
| `use_reranker` / `use_hybrid` / `use_graph` / `use_semantic_cache` | `true` | Ablation feature flags |

---

## Benchmarking

```bash
# List domains + QA pair counts
PYTHONPATH=. python run_benchmark_now.py --list

# Full 18-question run per domain (fast model)
PYTHONPATH=. python run_benchmark_now.py --domain second_brain
PYTHONPATH=. python run_benchmark_now.py --domain exam_prep

# Smaller run
PYTHONPATH=. python run_benchmark_now.py --domain exam_prep --max-questions 6
```

Results land in `data/benchmarks/results_<domain>.json` and
`benchmark-results/<domain>.json` + `benchmark-results/summary.md`
(accuracy, latency, Recall@5, MRR, retrieval success, per-category accuracy).

QA pairs live in `data/benchmarks/qa_pairs_<domain>.json` (18 per domain:
6 direct lookup, 6 cross-reference, 6 synthesis — grounded in actual source
material).

---

## Docker

```bash
docker build -t synapse .
docker run -p 8000:8000 \
  -e NVIDIA_API_KEY_1=nvapi-xxx \
  -e ADHD_CURE_ROOT=/data \
  -v synapse-data:/app/data \
  synapse
```

Deployment targets a **stateful** environment (Railway or Render) — the stack
needs persistent disk for `data/chroma_db`, `data/*.json`, and `data/synapse.db`.
Vercel cannot run the FastAPI backend. The Dockerfile seeds `/app/data_seed`
on first boot so pre-built collections survive container restarts when a volume
is mounted at `/app/data`.

---

## Tests

```bash
PYTHONPATH=. pytest tests/ -q        # 120 tests
cd web && npx tsc --noEmit           # frontend typecheck
cd ../second-brain-agent && npx tsc --noEmit   # agent typecheck
```

Coverage: chunking, entity extraction (52), knowledge graph (25), query engine
(14), domain isolation (13), LLM routing (10), ChromaDB.

---

## License

MIT