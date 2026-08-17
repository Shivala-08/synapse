# Synapse — Build Roadmap
## ET AI Hackathon 2026 — Problem Statement 8

---

## 1. Complete Architecture

```
┌─────────────────────┐
│   Document corpus    │  PDFs, CSVs, DOCX (safety manuals, work orders,
│                       │  permits, regulatory docs, incident reports)
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│  Ingestion pipeline   │  Parse → clean → chunk
│  (pdfplumber/pandas/  │
│   python-docx)        │
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     │           │
┌────▼─────┐ ┌───▼──────────┐
│ Embedding │ │Entity        │
│ (sentence-│ │extraction    │
│transformer)│ │(spaCy+regex)│
└────┬─────┘ └───┬──────────┘
     │           │
┌────▼─────┐ ┌───▼──────────┐
│ Vector    │ │ Knowledge    │
│ store     │ │ graph        │
│(ChromaDB) │ │(NetworkX)    │
└────┬─────┘ └───┬──────────┘
     │           │
     └─────┬─────┘
           │
┌──────────▼───────────┐
│    Query engine       │  Retrieve top-k chunks + traverse
│                       │  graph for related entities
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│   Claude API call     │  Assembles context → structured JSON:
│                       │  {answer, sources[], confidence}
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│    Streamlit UI       │  Chat + citations + confidence badges
│                       │  + graph view + upload panel
└───────────────────────┘
```

**Two parallel paths, one merge point** — this is the core technical story for judges. The vector path answers "what does the document say" questions; the graph path answers "how does X relate to Y" questions. Most competing teams will only build the vector path.

---

## 2. Complete API Endpoint List (FastAPI)

| Method | Endpoint | Purpose | Returns |
|---|---|---|---|
| `POST` | `/ingest/upload` | Upload one or more documents; triggers parse → chunk → embed → extract → graph-update pipeline | `{doc_id, status, chunks_created, entities_found}` |
| `GET` | `/documents` | List all ingested documents with metadata | `[{doc_id, filename, type, upload_date, chunk_count}]` |
| `GET` | `/documents/{doc_id}` | Get full detail + chunks for one document | `{doc_id, filename, chunks: [...]}` |
| `POST` | `/query` | Main RAG endpoint — ask a natural language question | `{answer, sources: [{doc_id, excerpt}], confidence, entities_used}` |
| `GET` | `/graph` | Full knowledge graph as nodes/edges JSON, for visualization | `{nodes: [...], edges: [...]}` |
| `GET` | `/graph/entity/{entity_id}` | Subgraph centered on one entity (e.g. one equipment tag) | `{center, neighbors: [...]}` |
| `GET` | `/entities` | List all extracted entities by type | `{equipment: [...], permits: [...], regulations: [...]}` |
| `POST` | `/compliance/check` | (Stretch) Check a regulatory requirement against ingested procedures for gaps | `{requirement, compliant: bool, gaps: [...]}` |
| `GET` | `/benchmark/run` | Run the ground-truth Q&A set and return accuracy metrics | `{accuracy, avg_time_to_answer, failures: [...]}` |
| `POST` | `/feedback` | Log thumbs up/down on an answer (nice-to-have, shows iterative design thinking) | `{status: "logged"}` |
| `GET` | `/health` | Basic health check | `{status: "ok"}` |

Debug-only, don't expose in the demo UI but useful while building:
| `GET` | `/debug/search?q=` | Raw vector similarity search, no LLM call — for tuning chunk size / top-k |

---

## 3. Free Resources (everything below costs $0)

**LLM / generation**
- Anthropic Claude API — new accounts get initial free credits; check if the hackathon organizers are distributing API credits for the event (common for AI hackathons — worth emailing organizers day 1)
- Ollama running Llama 3.1 8B or Mistral 7B locally — free, no key, good for heavy iteration/testing so you don't burn API credits on every debug query, then switch to Claude for the final citation-quality answer generation

**Embeddings**
- `sentence-transformers` (`all-MiniLM-L6-v2`) — free, runs locally, no API key, no rate limit, works offline

**Vector store**
- ChromaDB — open source, file-based, zero infrastructure setup

**Entity extraction / NLP**
- spaCy (`en_core_web_sm`) — free NER model
- Regex for domain-specific IDs (equipment tags, permit numbers, OISD section references) — spaCy alone won't catch these patterns

**Knowledge graph**
- NetworkX — free, in-memory graph library
- `streamlit-agraph` or `pyvis` — free graph visualization components that embed directly in Streamlit

**OCR (only if you attempt the P&ID stretch goal)**
- Tesseract OCR or EasyOCR — both free

**Frontend**
- Streamlit — free, open source
- Streamlit Community Cloud — free hosting if you want a public URL for judges

**Hosting alternatives**
- Hugging Face Spaces — free hosting for Streamlit/Gradio apps
- Render.com or Railway — free tiers for the FastAPI backend if you split frontend/backend
- ngrok — free tunnel if you just want to demo from a laptop with a public link as backup

**Synthetic data**
- Faker (Python library) — free, generates realistic names, dates, IDs for your synthetic work orders and permits

**Public real documents (for authenticity)**
- OISD standards, DGMS publications, Factory Act text — all publicly downloadable PDFs, free
- CPCB / regulatory guidance documents — free public downloads

**Diagrams, slides, video**
- draw.io or Excalidraw — free architecture diagram tools
- Google Slides or Canva free tier — deck
- OBS Studio — free screen recording for your backup demo video

**Version control**
- GitHub (free, private repos included on free tier)

---

## 4. Seven-Day Roadmap — Two-Person Split
 
**Person A = coder** (backend, ML, pipeline, API)
**Person B = friend** (data, frontend, docs, benchmarking)

### Day 1 — Foundations
| Person A | Person B |
|---|---|
| Set up repo, Python venv, `requirements.txt` | Collect public regulatory PDFs (OISD/DGMS/Factory Act) + a safety manual template |
| FastAPI skeleton with `/health` working | Write Faker-based synthetic data generator for work orders, permits, inspection logs (CSV) |
| Test ChromaDB locally with a dummy document | Draft first pass of 15–20 benchmark Q&A pairs with known correct answers |
**End-of-day sync:** repo pushed to GitHub, corpus folder has 40+ real + synthetic documents.

### Day 2 — Ingestion pipeline
| Person A | Person B |
|---|---|
| Build parsers (pdfplumber, pandas, python-docx) | Finish and clean the full corpus; make sure entity names (equipment tags) recur across document types |
| Implement chunking (LlamaIndex) + embedding + Chroma storage | Refine benchmark Q&A set with exact source doc references |
| Implement `/ingest/upload` and `/documents` endpoints | Start Streamlit skeleton — chat input box, message history, empty layout |
**End-of-day sync:** full corpus ingests without errors; chunk counts look reasonable.

### Day 3 — Entities and graph
| Person A | Person B |
|---|---|
| Build spaCy + regex entity extractor (equipment tags, permit numbers, regulation refs) | Continue Streamlit UI — citation display component, confidence badge styling |
| Build NetworkX graph construction from extracted entities/relations | Draft architecture diagram slide (based on section 1 above) |
| Implement `/graph` and `/entities` endpoints | Test the UI shell with hardcoded dummy answers |
**End-of-day sync:** graph JSON is inspectable and has sensible nodes/edges; UI shell renders.

### Day 4 — Query engine (core feature, most important day)
| Person A | Person B |
|---|---|
| Build query engine: vector retrieval + graph traversal merge | Connect Streamlit frontend to the live `/query` endpoint |
| Integrate Claude API call with structured JSON output (answer/sources/confidence) | Manually test 20+ varied questions, log failures/weird answers for Person A |
| Implement `/query` endpoint end-to-end | Render citations and confidence badges in the UI |
**End-of-day sync:** a real question typed into the UI returns a cited, confidence-scored answer.

### Day 5 — Graph visualization + polish
| Person A | Person B |
|---|---|
| Prep `/graph/entity/{id}` for visualization | Integrate `streamlit-agraph`/`pyvis` graph view into the UI |
| Attempt compliance-check stretch feature (`/compliance/check`) if on schedule | Polish UI — colors, layout, loading states |
| Harden error handling (bad uploads, empty queries) | Start slide deck outline (problem → solution → architecture → demo → metrics) |
**End-of-day sync:** feature-complete app; graph is visible and clickable in the UI.

### Day 6 — Evaluation + materials
| Person A | Person B |
|---|---|
| Run the 15–20 question benchmark script, compute accuracy + time-to-answer | Build final slide deck with real screenshots and benchmark numbers |
| Fix any low-scoring cases; tune chunk size / top-k | Write the 3-minute demo script |
| Optimize response latency | Record backup demo video with OBS in case live demo fails |
**End-of-day sync:** benchmark numbers documented; backup video exists.

### Day 7 — Rehearsal and buffer
| Both together |
|---|
| Full dry run of the live demo, end to end |
| Fix any last bugs found during rehearsal |
| Time the pitch to fit 3 minutes |
| Confirm fallback plan (cached answers or backup video) in case of live failure |
| Submit |

---

## 5. Quick Reminders for the Pitch

- Lead with the fragmentation stat from the problem context (7–12 disconnected systems per plant) — it's already handed to you.
- Show one question that pulls from two different document types in a single cited answer — this is the moment that differentiates you from a plain PDF chatbot.
- Close on your actual benchmark numbers (accuracy %, time-to-answer vs. manual search), not adjectives.

---

## 6. Production Scaling Strategy (The 5 Pillars)

To transition this high-performance prototype into a production-grade, enterprise RAG system processing millions of documents, the architecture must scale across five critical dimensions:

### 1️⃣ Asynchronous Offline Ingestion Pipeline
In production, document ingestion is entirely decoupled from the query/request path to ensure sub-second response times:
*   **Storage Streaming**: Ingest pipelines monitor object storage buckets (Amazon S3 / Google Cloud Storage) using event notifications (e.g., SQS/PubSub) to stream new files.
*   **On-Demand OCR**: Optical Character Recognition (OCR) is applied selectively (via Tesseract/EasyOCR) only for scanned image PDFs or diagrams, passing standard PDFs/DOCX directly to lightweight text extractors to minimize compute.
*   **Text Cleaning & Normalization**: Standardizes character sets, strips formatting noise, and cleans up document headers/footers.
*   **Intelligent Semantic Chunking**: Replaces fixed-token boundaries with layout-aware chunking (detecting section headers, tables, and lists) to keep semantically related rules intact.
*   **Rich Metadata Schema**: Every chunk is indexed with metadata tags including `doc_id`, `page_number`, `section_header`, `author`, `last_modified`, and extracted `equipment_tags`.

### 2️⃣ Enterprise-Scale Embedding & Indexing
Embeddings are computed offline in batch jobs using queue-based workers (with GPU acceleration):
*   **Batch Queuing**: New chunks are queued in Redis/RabbitMQ and processed in batches by dedicated workers to maximize GPU utilization.
*   **Distributed ANN Indexes**: The local ChromaDB store scales up to a distributed vector database (Milvus, Qdrant, Vespa, or Elasticsearch).
*   **Index Tuning**: Vectors are sharded and indexed using high-performance algorithms such as **HNSW** (Hierarchical Navigable Small World) for search speed, combined with **IVF-PQ** (Inverted File Product Quantization) to compress vector memory footprints at scale.
*   **Metadata Filtering**: Crucially, **metadata filtering serves as the first gate** (filtering on equipment types, plant locations, or document types). Vector search is only utilized as a fallback for semantic matches.

### 3️⃣ Minimalist Request Path
The user query pathway is kept highly optimized and tight:
$$\text{Query} \rightarrow \text{Metadata Filter} \rightarrow \text{Cache Lookup} \rightarrow \text{ANN Vector Search} \rightarrow \text{Reranking} \rightarrow \text{LLM Generation}$$
*   **Bypassing Vector Search**: Queries with exact metadata filters (e.g., specific work orders or permit IDs) bypass vector search entirely.
*   **Context Volume Control**: Rather than dumping dozens of matches, the system retrieves a slightly larger candidate set (8-10 chunks), re-ranks them locally, and sends a **maximum of 5–10 chunks** to the LLM. Keeping the context window compact reduces LLM processing costs and prevents model confusion.

### 4️⃣ Multi-Tier Caching Architecture
Caching is deployed at multiple layers to drive down latency and API costs:
*   **Query-to-Answer Cache**: An in-memory rolling semantic cache (like our current implementation using cosine similarity $\ge 0.95$) checks queries before any database calls.
*   **Query-to-Retrieval Cache**: Caches the top retrieved chunks for popular queries/topics so that recurring topics bypass vector index lookups.
*   **Data/Index Cache**: Caches parsed document sections and hot vector indexes in fast Redis memory for rapid traversal.

### 5️⃣ Observability & Continuous Monitoring
To prevent silent degradation as data and model versions evolve:
*   **Retrieval Monitoring**: Measures $Recall@k$ and Mean Reciprocal Rank (MRR) using synthetic benchmark checks.
*   **Answer Quality**: Tracks user thumbs up/down feedback and logs low-confidence LLM outputs for manual inspection.
*   **Performance Metrics**: Monitors cache hit rates, P95 latency, and GPU/API rate limit usage.
*   **Re-indexing Cycles**: Periodically re-shards indexes and re-embeds the corpus when major model upgrades occur.

