# Engineering Log

Every entry follows the same shape: **Problem → Attempt → Result → Fix → Lesson**.
These are the failures that shaped the system — the things that were tried,
broke, and got fixed, in roughly chronological order. Nothing here is
reconstructed from memory alone; each entry cites the code or commit it came from.

---

## 1. Keyword-overlap scoring was brittle

- **Problem:** Early answer scoring used keyword overlap between the generated
  answer and the expected answer. Plural/singular mismatches ("compressor" vs
  "compressors") and paraphrases produced false negatives, capping benchmark
  accuracy at 77.8% (14/18).
- **Attempt:** Tuning the overlap threshold. It only moved which questions
  failed, not the failure mode.
- **Result:** Same accuracy, new failures.
- **Fix:** Replaced with embedding cosine similarity (≥ 0.55) between answers —
  semantically equivalent phrasing now scores as a match (`settings.similarity_threshold`,
  `run_benchmark_now.py`).
- **Lesson:** If your grader is lexical, your system will be optimized for
  lexical luck. Semantic scoring is necessary — but see #9 for why it isn't
  sufficient on its own.

## 2. Scanned PDFs extract zero characters

- **Problem:** `OISD-GDN-192.pdf` is a scanned image with no text layer;
  `pdfplumber` returned 0 characters, so the document silently vanished from
  the corpus.
- **Attempt:** A pre-check script (`check_pdfs.py`) inspected font-layer
  metadata to classify each PDF as digital or scanned before ingestion.
- **Result:** Confirmed 1 of 6 regulatory PDFs was scanned; naive OCR was out
  of scope for the deadline.
- **Fix:** Provided a verified text transcription (`OISD-GDN-192.txt`) and
  ingested that instead, so the document participates fully in chunking,
  embedding, and graph construction.
- **Lesson:** Validate your inputs before you trust your parser. A document
  that ingests with zero bytes is worse than one that errors loudly.

## 3. Rate limits strike mid-stream, not at init

- **Problem:** NVIDIA NIM rate limits (`ResourceExhausted`) surface *during
  token iteration* of a streaming response, not when the client is created.
  Key rotation that only wrapped initialization never caught them — the user
  saw a half-answer and an error box.
- **Attempt:** Initially catching the error after the stream finished. Too
  late — the UI had already rendered a broken partial response.
- **Result:** Confirmed the failure only manifests inside
  `for chunk in completion`.
- **Fix:** Wrapped the stream-iteration loop in a retry block; on exhaustion
  mid-response, the next key (of 10) takes over and the stream resumes
  (`_find_working_client()` in `llm.py`, shared by both `generate()` and
  `stream_generate()`).
- **Lesson:** For streaming integrations, the failure point is the loop, not
  the connection. This was the subtlest bug in the project — a great
  "hard bug" interview story because it required understanding the async
  life cycle of the API client.

## 4. Which text feeds the knowledge graph: query or chunks?

- **Problem:** Graph traversal started from entities in the *query text*
  alone. Queries phrased without exact entity names ("what are the safety
  rules for that pump?") found nothing in the graph, so graph context was
  frequently empty.
- **Attempt:** Adding a query-side regex fallback for equipment tags and
  regulation codes. Helped exact-ID queries, not paraphrases.
- **Result:** Better, still incomplete.
- **Fix:** Extracted entities from the *retrieved chunks' metadata* as well
  (entity IDs are written to each chunk at ingestion) and merged both sets
  before traversal (`retrieve_context()` in `query_engine.py`).
- **Lesson:** The graph is only as reachable as the anchor points you give
  it. Anchoring traversal to retrieved evidence instead of the user's exact
  words is what made cross-document answers possible.

## 5. Render OOM (status 137) → remote embeddings

- **Problem:** The deployment host (Render, ~512 MB) died with status 137
  (OOM) during startup — loading PyTorch + sentence-transformers for
  embeddings plus the model weights blew the memory budget.
- **Attempt:** Slimming model sizes and lazy-loading. Marginal.
- **Result:** Still OOM.
- **Fix:** Migrated embeddings to the Hugging Face Inference API, removing
  PyTorch/sentence-transformers from the deployed footprint entirely.
- **Lesson:** "It works on my machine" is a memory claim, not just a code
  claim. The deployment budget forced an architectural change that local
  development never would have surfaced.

## 6. Silent zero-vector corruption (found during the revamp)

- **Problem:** When the HF Inference API was unreachable, the embedder logged
  a warning and returned **zero vectors**. The committed ChromaDB index was
  rebuilt during such a session — every one of its 406 embeddings was `[0,0,…]`,
  so every query returned cosine distance 1.0 and arbitrary documents.
- **Attempt:** N/A — discovered by spot-checking retrieval during the
  evaluation-harness work (query returned distance 1.0 for unrelated docs).
- **Result:** The "pre-built index" the deployment seeds from was garbage.
- **Fix:** Embedder now falls back to a local `sentence-transformers` model
  instead of returning zeros (`src/pipeline/embedder.py`); the index was
  rebuilt offline and verified (correct doc at 0.409 distance for a known
  query).
- **Lesson:** A fallback that returns *valid-shaped garbage* is more dangerous
  than a hard failure. Zero vectors pass every shape check and silently break
  everything downstream. If you degrade, degrade loudly — or not at all.

## 7. The knowledge graph was 68% junk

- **Problem:** spaCy mislabeled PDF-extracted fragments — roman numerals
  (`vii`, `xviii`), single letters (`gb`, `lo`), lowercase headings
  ("acetylene cylinder", "the united nations") — as PERSON/ORG. The graph had
  1,032 nodes, 710 of them junk "person" nodes.
- **Attempt:** Filtering with obvious rules (length, digits). Missed
  column-spanning spans and lowercase multi-word fragments.
- **Result:** Junk persisted, just less of it.
- **Fix:** A heuristic `is_valid_person_entity()` (roman numerals, digit-laden
  fragments, single letters/state codes, heavy punctuation, all-lowercase
  fragments, column/address words, line-spanning spans) applied at extraction,
  plus a graph fix so nodes auto-created by `add_edge` before their
  `add_entity` call get typed (25 entities previously rendered untyped).
  Rebuilt: 1,032 → 533 nodes, person nodes 710 → 211.
- **Lesson:** NER output is a hypothesis, not a fact. In a domain with noisy
  extracted text, entity quality gates every downstream feature — the graph,
  the UI, and retrieval.

## 8. A one-character crash in the personnel fallback

- **Problem:** `_extract_personnel()` called `names.add(...)` on a Python
  `list`, raising `AttributeError` whenever spaCy returned no PERSON/ORG and
  the text contained "Mr./Ms./Dr.". It was unguarded in `retrieve_context()`,
  so a query like "Mr. X…" could 500 the API.
- **Attempt:** N/A — reproduced it in 30 seconds once the code was read
  (`tests/test_extractor.py` has the regression test).
- **Result:** `'list' object has no attribute 'add'`.
- **Fix:** `append`, plus guards around both unguarded `extract_entities()`
  call sites (query engine and compliance checker) so entity extraction can
  never take down an endpoint.
- **Lesson:** The code path was only ever exercised in production — tests
  always had spaCy's model loaded, so the fallback was never covered. This is
  the argument for testing fallback branches explicitly.

## 9. The reranker was silently disabled by a missing dependency

- **Problem:** `query_engine.py` imports `sentence_transformers` for the
  cross-encoder, but it wasn't in `requirements.txt`. On a fresh install the
  import failed, was swallowed by the `except`, and re-ranking silently
  degraded to hybrid-score sorting.
- **Attempt:** N/A — caught during a dependency audit.
- **Result:** The system's biggest accuracy contributor (see `EVALUATION.md`)
  was dead code on every fresh install.
- **Fix:** Restored `sentence-transformers` to requirements and dropped the
  stale `streamlit-agraph`. A lazy import would also have made the dependency
  explicit.
- **Lesson:** Silent `except` blocks hide missing dependencies as gracefully
  degraded features. If a feature is optional, make the degradation visible
  (log + metric), not invisible.

## 10. Cold-start variance caused a phantom regression

- **Problem:** After corpus re-initialization, benchmark questions Q004 and
  Q016 dropped to ~0.3–0.5 similarity (below the 0.55 threshold) — a "regression".
- **Attempt:** Investigating chunking and duplicate-embedding changes.
  Moving an archived duplicate file out of the corpus helped, but questions
  still flickered across runs.
- **Result:** Root cause was cold-start retrieval variance: empty model caches
  and first-query model loading changed which chunks ranked top.
- **Fix:** A 5-query warm-up phase before benchmark timing, and retrieval
  source logging (`data/benchmarks/retrieval_log.json`) so future
  "regressions" can be checked against actual retrieved chunks instead of
  guessed at.
- **Lesson:** Benchmark a system in its steady state, and always record what
  was retrieved — not just the final score. Without the log, we'd still be
  chasing a ghost.

---

## What this log is for

The through-line: every component that stayed in the final system earned its
place by surviving a failure — the reranker by being restored after a silent
dependency loss, the graph by being cleaned after a junk-entity flood, the
hybrid search by surviving the scoring-metric swap. The ablation study in
`EVALUATION.md` is the quantitative version of this story; this log is the
qualitative one.
