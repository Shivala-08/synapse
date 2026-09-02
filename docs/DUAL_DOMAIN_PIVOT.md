# Synapse Dual-Domain Pivot: Build Manual

**Goal:** Make Synapse run two domains from one codebase. A **Second Brain**
(Obsidian + Claude Code vault) and an **Exam Prep Engine** (Newton School
coursework). Switch domains by config. Do not fork code.

This manual is a build spec for Claude Code, Cursor, or Windsurf. Execute
top to bottom. Each phase has a checkpoint. Do not skip checkpoints.

---

## 0. Prerequisites

- [ ] Synapse repo cloned. `./start.sh` runs clean.
- [ ] Obsidian installed. Vault created. `CLAUDE.md` written with folders
      `raw/`, `wiki/`, `output/`, plus compile/query/audit rules.
- [ ] 3–5 real notes compiled into `wiki/`. Run one `compile` pass first.
      You need real `.md` files with `[[wikilinks]]` before you touch code.
- [ ] Exam prep material ready: syllabus PDFs, notes, past PT papers.

---

## Phase 1: Domain Profile Config

**Why:** One engine, N domains. `parser.py`, `chunker.py`, `embedder.py`,
and `llm.py` do not change. Only the data and entity types change per domain.

### 1.1 Create `domains/` folder

```
synapse/
└── domains/
    ├── second_brain.yaml
    └── exam_prep.yaml
```

### 1.2 `domains/second_brain.yaml`

```yaml
domain_id: second_brain
display_name: "Second Brain"
source_path: "/absolute/path/to/obsidian-vault/wiki"
source_types: [".md"]
collection_name: "second_brain_vectors"
graph_file: "data/second_brain_knowledge_graph.json"
entity_types:
  - Project
  - TechStack
  - BugFix
  - APIIntegration
  - Decision
link_syntax: wikilink        # triggers [[Note Name]] parsing in extractor.py
chunk_size: 512              # notes are short; use 512, not 1024
chunk_overlap: 100
```

### 1.3 `domains/exam_prep.yaml`

```yaml
domain_id: exam_prep
display_name: "Exam Prep"
source_path: "/absolute/path/to/exam-materials"
source_types: [".pdf", ".docx", ".txt"]
collection_name: "exam_prep_vectors"
graph_file: "data/exam_prep_knowledge_graph.json"
entity_types:
  - Subject
  - Topic
  - Formula
  - PastQuestion
link_syntax: none             # no manual links; use auto-extraction only
chunk_size: 1024
chunk_overlap: 200
```

### 1.4 Extend `src/config.py`

Add a `DomainProfile` Pydantic model and a loader function:

```python
from pydantic import BaseModel
import yaml
from pathlib import Path

class DomainProfile(BaseModel):
    domain_id: str
    display_name: str
    source_path: str
    source_types: list[str]
    collection_name: str
    graph_file: str
    entity_types: list[str]
    link_syntax: str = "none"
    chunk_size: int = 1024
    chunk_overlap: int = 200

def load_domain_profile(domain_id: str) -> DomainProfile:
    path = Path(f"domains/{domain_id}.yaml")
    with open(path) as f:
        return DomainProfile(**yaml.safe_load(f))

def list_domains() -> list[str]:
    return [p.stem for p in Path("domains").glob("*.yaml")]
```

**Checkpoint:**
```bash
python -c "from src.config import load_domain_profile; print(load_domain_profile('second_brain'))"
```
This prints a valid `DomainProfile` object. If it fails, fix the YAML
format or the loader before you continue.

---

## Phase 2: Namespace Storage by Domain

**Why:** Second Brain and Exam Prep data must not share a vector collection
or graph file. Each domain needs its own storage.

### 2.1 `src/storage/chroma_store.py`

Change the collection name to come from `DomainProfile`, not from a
hardcoded string:

```python
class ChromaStore:
    def __init__(self, domain_profile: DomainProfile):
        self.client = chromadb.PersistentClient(path="data/chroma_db")
        self.collection = self.client.get_or_create_collection(
            name=domain_profile.collection_name
        )
```

### 2.2 `src/graph/knowledge_graph.py`

Same change. The graph file path comes from `domain_profile.graph_file`:

```python
class KnowledgeGraph:
    def __init__(self, domain_profile: DomainProfile):
        self.graph_path = domain_profile.graph_file
        self.graph = self._load_or_create()
```

### 2.3 Wire domain profile into ingestion

`src/pipeline/ingest.py` takes `domain_profile` as a constructor argument.
It passes the profile to `ChromaStore` and `KnowledgeGraph`.

`parser.py`, `chunker.py`, and `embedder.py` do not know about domains.
They process whatever text you give them.

**Checkpoint:** Ingest one dummy `.md` file for each domain. Confirm two
separate collections exist in ChromaDB. Confirm two separate graph JSON
files exist under `data/`.

---

## Phase 3: Wikilink Parsing (Second Brain only)

**Why:** This is the differentiator. The graph builds from both manual
`[[wikilinks]]` and automatic spaCy/regex extraction. Neither Obsidian
nor a plain RAG tool does this alone.

### 3.1 `src/pipeline/extractor.py`

Add a wikilink pass. Gate it on `domain_profile.link_syntax == "wikilink"`:

```python
import re

WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")

def extract_wikilinks(text: str) -> list[str]:
    """Return note names from [[Note Name]] syntax."""
    return [m.strip() for m in WIKILINK_PATTERN.findall(text)]
```

When `link_syntax == "wikilink"`, do the following for each chunk:
1. Run `extract_wikilinks()` on the chunk text.
2. Treat each returned name as a node. Use the note's folder or
   frontmatter for the type. Use `Note` if you cannot determine the type.
3. Add an edge `(source_note) --[LINKS_TO]--> (target_note)`.
4. Keep all spaCy/regex entity edges too.

**Checkpoint:** Ingest a note that contains `[[Some Other Note]]`. Confirm
the graph has a `LINKS_TO` edge. Confirm it also has auto-extracted entity
edges.

---

## Phase 4: UI Domain Switcher

### 4.1 `src/app.py` (Streamlit)

Add a selectbox at the top of the sidebar. Put it before any other
component:

```python
import streamlit as st
from src.config import list_domains, load_domain_profile

domain_id = st.sidebar.selectbox("Domain", list_domains())
domain_profile = load_domain_profile(domain_id)
st.sidebar.caption(f"Active: {domain_profile.display_name}")
```

Pass `domain_profile` to `ChromaStore`, `KnowledgeGraph`, and the query
engine. Streamlit reruns top to bottom when the selectbox changes. The
right collection and graph load automatically.

### 4.2 `src/main.py` (FastAPI)

Accept a `domain_id` query param or header on `/query` and `/query/stream`.
Default to `second_brain` if the caller does not send one.

**Checkpoint:** Switch the dropdown in the running app. Confirm the graph
nodes change. Confirm query answers change.

---

## Phase 5: Ingest Both Corpora

### 5.1 Second Brain

```bash
PYTHONPATH=. python rebuild_knowledge_graph.py --domain second_brain
```
Set `source_path` in `second_brain.yaml` to your Obsidian vault's `wiki/`
folder. Re-run after every `compile` pass to keep Synapse's copy current.
Or set up a cron job for nightly re-ingestion.

### 5.2 Exam Prep

```bash
PYTHONPATH=. python rebuild_knowledge_graph.py --domain exam_prep
```
Set `source_path` to your syllabus PDFs, notes, or past PT papers folder.

**Checkpoint:** Open the Document Library tab for each domain. Confirm the
file counts, chunk counts, and entity counts match what you ingested.

---

## Phase 6: Benchmark Both Domains

### 6.1 Create two ground-truth sets

Create `data/benchmarks/qa_pairs_second_brain.json` and
`data/benchmarks/qa_pairs_exam_prep.json`. Put 15–20 questions in each.
Use three question types:

| Type | Second Brain example | Exam Prep example |
|---|---|---|
| Direct lookup | "What was the fix for the n8n Sheets tool node?" | "What is Bayes' theorem?" |
| Cross-reference | "How do Udhaar's Twilio auth and RIYA's voice pipeline relate?" | "How do binary search and recursion relate?" |
| Synthesis | "What patterns repeat across my API integrations?" | "What topics repeat across past PT-1 papers?" |

### 6.2 Run the benchmark per domain

```bash
PYTHONPATH=. python run_benchmark_now.py --domain second_brain
PYTHONPATH=. python run_benchmark_now.py --domain exam_prep
```
Add a `--domain` flag to `run_benchmark_now.py`. Load the matching profile
and `qa_pairs` file. Use the same pattern as Phase 1.

**Checkpoint:** You get two accuracy and latency tables. One per domain.
Both come from the same retrieval pipeline. These tables prove the
architecture works across domains.

---

## Phase 7: README Rewrite

Replace the current industrial-only framing. Use this structure:

1. **One-line pitch:** "One hybrid retrieval engine. Two live domains.
   A Second Brain from Obsidian + Claude Code. An Exam Prep assistant
   from my coursework. Swap the config, not the code."
2. **Benchmark table from Phase 6.** Put it before the architecture
   diagram. Lead with proof, not explanation.
3. **Architecture diagram.** Keep it. Relabel node types as
   "configurable per domain."
4. **Industrial domain.** Keep it as `domains/industrial.yaml`. Do not
   delete it. More domains = stronger claim.
5. **"Why not use Obsidian / Claude Code alone?"** One paragraph. Name
   the second-brain pattern. List what Synapse adds: confidence scores,
   Recall@5/MRR, cross-encoder re-ranking, adaptive routing, visual
   graph exploration.

---

## Phase 8: Redeploy

- [ ] Push to Railway or Render. Use the existing `Dockerfile`. Vercel
      cannot run this stack. It needs stateful FastAPI + Streamlit.
- [ ] Set environment variables: NVIDIA NIM keys, domain `source_path`
      overrides for production.
- [ ] Mount a volume for `data/chroma_db` and `data/*.json` graph files.
      Confirm both domain collections survive restarts.
- [ ] Smoke test: switch domains in the deployed UI. Run one query in
      each domain.

---

## Execution Order

```
1. Obsidian vault has real content              (prerequisite)
2. domains/*.yaml + config.py loader            → Checkpoint: profile loads
3. Namespaced ChromaStore + KnowledgeGraph      → Checkpoint: 2 collections, 2 graphs
4. Wikilink extractor pass                      → Checkpoint: LINKS_TO edges appear
5. UI domain switcher                           → Checkpoint: switching changes results
6. Ingest both corpora                          → Checkpoint: doc counts correct
7. Benchmark both domains                       → Checkpoint: 2 tables
8. README rewrite                               → Checkpoint: pitch leads with proof
9. Redeploy on Railway/Render                   → Checkpoint: live, both domains work
```

Do not skip checkpoints. Each one takes less than 5 minutes. Skipping
verification is how the "0 characters extracted" and "black canvas crash"
bugs happened the first time.
