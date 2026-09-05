# ADHD-CURE
# Master Autonomous Build Manual
## Second Brain + Agent TUI + Synapse Dual-Domain Retrieval

Version: 1.0

---

# 0. MISSION

You are the primary autonomous engineering agent for the `adhd-cure`
workspace.

Your job is to take the existing workspace from its current partially
completed state to a fully tested, integrated, documented, and deployment-
ready system.

The workspace contains three related but separate components:

    adhd-cure/
    ├── synapse/
    ├── second-brain/
    └── second-brain-agent/

Their responsibilities are:

    second-brain/
        Human-readable local knowledge vault.

    second-brain-agent/
        AI librarian / compiler / organizer for the vault.

    synapse/
        Shared hybrid retrieval and knowledge-intelligence engine.

DO NOT merge these into one codebase.

DO NOT replace Synapse with the Agent TUI.

DO NOT replace the Second Brain vault with a vector database.

DO NOT build separate retrieval engines for each domain.

The final architecture must be:

                 ┌─────────────────────┐
                 │   SECOND BRAIN      │
                 │   Obsidian Vault    │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Second Brain Agent  │
                 │       TUI           │
                 │ librarian/compiler  │
                 └──────────┬──────────┘
                            │
                            ▼
                    wiki/*.md files
                            │
                            ▼
                 ┌─────────────────────┐
                 │      SYNAPSE        │
                 │ Shared RAG Engine   │
                 └──────────┬──────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
           Vector          BM25         Graph
           Search         Search        Search
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                       Reranking
                            │
                            ▼
                         Answer


Exam Prep uses the exact same Synapse retrieval engine:

    Exam Materials
          │
          ▼
       Synapse
          │
    exam_prep domain
          │
          ▼
       Answer

The only domain-specific pieces should primarily be configuration,
source data, entity types, link syntax, and storage namespaces.

---

# 1. CURRENT WORKSPACE

The expected workspace is:

    ~/Desktop/adhd-cure/

with:

    ~/Desktop/adhd-cure/synapse
    ~/Desktop/adhd-cure/second-brain
    ~/Desktop/adhd-cure/second-brain-agent

Before changing anything, verify this.

Run:

    pwd
    ls -la
    find . -maxdepth 2 -type d | sort

If the structure differs, inspect it before making assumptions.

---

# 2. ABSOLUTE RULES

## 2.1 Preserve existing work

Never blindly:

    rm -rf
    git reset --hard
    delete databases
    replace entire directories
    rewrite Synapse from scratch

Do not destroy existing industrial-corpus functionality.

Do not delete Second Brain raw material.

Do not overwrite knowledge unless explicitly required.

Prefer minimal modifications.

---

## 2.2 Inspect before changing

For every phase:

    inspect
        ↓
    understand
        ↓
    identify missing functionality
        ↓
    implement
        ↓
    test
        ↓
    verify
        ↓
    continue

Do not implement functionality that already exists.

---

## 2.3 No fake success

Never claim:

    COMPLETE
    WORKING
    VERIFIED
    PASSED

unless the corresponding functionality was actually tested.

If blocked:

    STATUS: BLOCKED

    Reason:
    ...

    Required human action:
    ...

Continue with independent work where possible.

---

# 3. HUMAN-IN-THE-LOOP POLICY

The system should automate as much of the engineering as possible.

The human should primarily provide:

    1. semantic approval of generated knowledge
    2. Exam Prep source materials/path
    3. credentials/secrets when required
    4. deployment choices
    5. decisions where ambiguity genuinely cannot be resolved

Do NOT ask the human for permission to:

    - inspect files
    - inspect source code
    - search repositories
    - create tests
    - fix obvious bugs
    - fix type errors
    - fix lint errors
    - write documentation
    - create reports
    - run local tests
    - create configuration
    - perform safe refactoring

---

# 4. HUMAN INPUT FORMAT

Whenever genuine human input is required, stop and print:

==================================================
HUMAN INPUT REQUIRED
==================================================

Reason:
<reason>

Decision:
<decision required>

Options:
A. ...
B. ...
C. ...

Recommended:
<recommended option>

No destructive action has been taken.
==================================================

Do not repeatedly ask for confirmation about the same decision.

---

# 5. PHASE 0 — WORKSPACE DISCOVERY

Start here.

Inspect all three projects.

For:

    synapse/

inspect:

    README.md
    requirements.txt
    Dockerfile
    start.sh
    src/
    tests/
    domains/
    data/
    run_benchmark_now.py
    rebuild_knowledge_graph.py

For:

    second-brain/

inspect:

    CLAUDE.md
    raw/
    wiki/
    output/

For:

    second-brain-agent/

inspect:

    package.json
    tsconfig.json
    src/
    agent.config.json
    .env.example

Create:

    PROJECT_STATE.md

containing:

    - current architecture
    - existing functionality
    - missing functionality
    - known errors
    - test status
    - integration risks
    - recommended execution order

Do not modify functional code during discovery.

---

# 6. PHASE 1 — SECOND BRAIN AGENT APPROVAL BUG

## Current known problem

The Agent TUI can read the vault and understand the vault rules.

It fails when attempting approved writes with:

    Tool(s) require approval but no state accessor is configured:
    file_write, file_write, ...

The problem is that write/edit tools require approval but the Agent SDK
call does not currently provide the required StateAccessor.

---

## 6.1 Inspect SDK

Inside:

    second-brain-agent/

determine the installed version of:

    @openrouter/agent

Inspect the actual installed SDK source/types for:

    StateAccessor
    approval
    requireApproval
    state
    tool approval

DO NOT guess the API.

Implement against the installed SDK version.

---

## 6.2 Implement approval workflow

The desired behavior is:

    Agent requests file_write
            ↓
    CLI receives approval request
            ↓
    Human approves/rejects
            ↓
    StateAccessor records state
            ↓
    approved tool executes

Approval must work for:

    file_write
    file_edit

Do not disable approval merely to eliminate the error.

---

## 6.3 Preserve vault sandboxing

The Agent must remain restricted to:

    second-brain/

Write and edit operations must not escape the vault.

Do not weaken filesystem safety.

---

## 6.4 Test

Run:

    cd second-brain-agent
    npx tsc --noEmit

Then:

    npm start

Test:

    Say exactly:
    "Second Brain agent online."

Then test a read-only request.

Then test:

    Create output/agent-test.md containing exactly:

    Agent write test.

    Do not modify anything else.

Verify:

    approval appears
    approval can be accepted
    file is created
    file is inside the vault
    unrelated files remain unchanged

Clean up only the temporary test artifact.

---

# 7. PHASE 2 — SECOND BRAIN COMPILATION

The Second Brain vault is the human-readable source of truth.

Read:

    second-brain/CLAUDE.md

before compiling.

Do not replace or weaken its rules.

---

## 7.1 Raw material

Inspect:

    second-brain/raw/

Compile all real Markdown source files.

Known current themes include:

    CampusHub
    Industrial AI
    JARVIS

Do not assume these are the only topics.

---

## 7.2 Compilation behavior

For every raw source:

    read
      ↓
    determine topic
      ↓
    create/select topic folder
      ↓
    create concise article
      ↓
    add [[wikilinks]]
      ↓
    update topic _index.md
      ↓
    update _master-index.md

Never delete raw files.

Never replace raw source with summaries.

Do not fabricate facts.

---

## 7.3 Required wiki structure

The result should resemble:

    second-brain/
    ├── raw/
    ├── wiki/
    │   ├── _master-index.md
    │   ├── campus-hub/
    │   │   ├── _index.md
    │   │   └── ...
    │   ├── industrial-ai/
    │   │   ├── _index.md
    │   │   └── ...
    │   └── jarvis/
    │       ├── _index.md
    │       └── ...
    └── output/

Adapt topic names to the actual content.

---

## 7.4 Article requirements

Articles should:

    - be concise
    - preserve important context
    - use clear sections
    - use lowercase-with-hyphens filenames
    - use [[wikilinks]]
    - avoid unnecessary duplication
    - end with:

        ## Key Takeaways

The Second Brain workflow is intended to turn messy source material into
structured, connected notes. 

---

## 7.5 Human semantic checkpoint

After compilation, present a concise report:

    Files processed:
    Topics created:
    Articles created:
    Wikilinks created:
    Potential ambiguities:

Only ask the human to review semantic issues.

Do not ask them to manually create the articles.

---

# 8. PHASE 3 — SECOND BRAIN VAULT AUDIT

Run an automated audit.

Check:

    - missing _index.md files
    - missing master-index references
    - broken [[wikilinks]]
    - empty articles
    - duplicate articles
    - orphaned articles
    - missing Key Takeaways sections

Create:

    second-brain/output/wiki-audit.md

Do not automatically alter knowledge just to make the audit clean.

Report semantic problems to the human.

---

# 9. PHASE 4 — SYNAPSE DOMAIN ARCHITECTURE

Inspect the current Synapse implementation before editing.

The target architecture is:

    domains/
    ├── second_brain.yaml
    └── exam_prep.yaml

The repository may already implement some or all of this.

Reuse existing functionality.

---

# 10. PHASE 5 — SECOND BRAIN DOMAIN PROFILE

Create or verify:

    synapse/domains/second_brain.yaml

Target:

    domain_id: second_brain
    display_name: "Second Brain"

    source_path:
      <absolute path to second-brain/wiki>

    source_types:
      - ".md"

    collection_name:
      second_brain_vectors

    graph_file:
      data/second_brain_knowledge_graph.json

    entity_types:
      - Project
      - TechStack
      - BugFix
      - APIIntegration
      - Decision

    link_syntax:
      wikilink

    chunk_size:
      512

    chunk_overlap:
      100

Do not hardcode the username if environment/config substitution is available.

---

# 11. PHASE 6 — EXAM PREP DOMAIN PROFILE

Create or verify:

    synapse/domains/exam_prep.yaml

Target:

    domain_id: exam_prep
    display_name: "Exam Prep"

    source_path:
      <exam material directory>

    source_types:
      - ".pdf"
      - ".docx"
      - ".txt"

    collection_name:
      exam_prep_vectors

    graph_file:
      data/exam_prep_knowledge_graph.json

    entity_types:
      - Subject
      - Topic
      - Formula
      - PastQuestion

    link_syntax:
      none

    chunk_size:
      1024

    chunk_overlap:
      200

If the Exam Prep source path is unknown:

    STOP

and ask the human for the local directory.

Do not invent a path.

---

# 12. PHASE 7 — DOMAIN PROFILE LOADER

Verify:

    synapse/src/config.py

supports:

    DomainProfile
    load_domain_profile()
    list_domains()

The model should support:

    domain_id
    display_name
    source_path
    source_types
    collection_name
    graph_file
    entity_types
    link_syntax
    chunk_size
    chunk_overlap

Test:

    python -c "
    from src.config import load_domain_profile
    print(load_domain_profile('second_brain'))
    print(load_domain_profile('exam_prep'))
    "

Both profiles must load successfully.

---

# 13. PHASE 8 — VECTOR STORAGE ISOLATION

Inspect:

    synapse/src/storage/chroma_store.py

Verify that the active DomainProfile controls the collection.

Required:

    second_brain_vectors
    exam_prep_vectors

These must be separate.

Do not allow:

    Second Brain documents
    +
    Exam Prep documents

inside one collection.

Create automated tests proving this.

---

# 14. PHASE 9 — GRAPH STORAGE ISOLATION

Inspect:

    synapse/src/graph/knowledge_graph.py

Verify that graph storage is domain-aware.

Target:

    data/second_brain_knowledge_graph.json
    data/exam_prep_knowledge_graph.json

Verify:

    - nodes are domain-specific
    - edges are domain-specific
    - graph reads use the active domain
    - graph writes use the active domain

Create tests proving cross-domain graph contamination cannot occur.

---

# 15. PHASE 10 — WIKILINK EXTRACTION

Inspect:

    synapse/src/pipeline/extractor.py

Verify parsing of:

    [[Note Name]]
    [[Note Name|Display Name]]
    [[Note Name#Heading]]

For:

    CampusHub uses [[React]] and [[FastAPI]].

the extractor should recognize:

    React
    FastAPI

as explicit links.

Do not remove normal entity extraction.

Wikilinks are an additional relationship layer.

---

# 16. PHASE 11 — LINKS_TO GRAPH EDGES

When:

    link_syntax: wikilink

the ingestion pipeline must generate:

    LINKS_TO

relationships.

Example:

    CampusHub
       |
       ├── LINKS_TO → React
       └── LINKS_TO → FastAPI

Automatic entities and wikilinks must coexist.

Test that at least one actual Second Brain note creates a real:

    LINKS_TO

edge.

---

# 17. PHASE 12 — BM25 DOMAIN ISOLATION

This is a critical phase.

Inspect:

    synapse/src/pipeline/query_engine.py

Search for:

    BM25
    bm25
    init_bm25_index_lazy
    get_vector_store

Audit every BM25 initialization path.

Potential bad architecture:

    get_vector_store()

without an active DomainProfile.

This can cause:

    Vector search → Second Brain
    BM25 → default/industrial collection

which is unacceptable.

---

## 17.1 Required BM25 behavior

BM25 must be domain-aware.

Acceptable architecture:

    BM25_INDEXES = {
        "second_brain": ...,
        "exam_prep": ...
    }

or an equivalent implementation.

Requirements:

    - indexes are domain-specific
    - one domain cannot overwrite another
    - switching domains cannot reuse stale indexes
    - rebuilds are domain-specific
    - queries use the selected domain

Write regression tests.

---

# 18. PHASE 13 — DOMAIN-AWARE QUERY ENGINE

Trace:

    UI/API
      ↓
    domain_id
      ↓
    DomainProfile
      ↓
    Vector
      ↓
    BM25
      ↓
    Graph
      ↓
    Reranker
      ↓
    Answer

Every layer must receive the correct domain.

Inspect:

    src/main.py
    src/App.py
    src/pipeline/query_engine.py
    src/storage/chroma_store.py
    src/graph/knowledge_graph.py

Eliminate hidden defaults that override an explicit domain.

---

# 19. PHASE 14 — STREAMLIT DOMAIN SELECTOR

Verify:

    synapse/src/App.py

contains a domain selector.

Target behavior:

    Domain:
    [ Second Brain ▼ ]

or:

    Domain:
    [ Exam Prep ▼ ]

Changing the domain must change:

    - vector collection
    - BM25 index
    - graph
    - query context
    - answer

Do not duplicate the application for each domain.

---

# 20. PHASE 15 — FASTAPI DOMAIN SUPPORT

Inspect:

    synapse/src/main.py

Ensure query endpoints support domain selection.

Preferred:

    /query?domain_id=second_brain
    /query?domain_id=exam_prep

and similarly for streaming queries.

If omitted, default to:

    second_brain

only where backward compatibility requires it.

Explicit domain selection must always win.

---

# 21. PHASE 16 — SECOND BRAIN INGESTION

Configure Second Brain source path to:

    ~/Desktop/adhd-cure/second-brain/wiki

or its actual absolute equivalent.

Use the repository's existing ingestion mechanism.

Preferred if supported:

    PYTHONPATH=. python rebuild_knowledge_graph.py --domain second_brain

Do not create duplicate ingestion systems.

---

## 21.1 Checkpoint

Report:

    Documents:
    Chunks:
    Entities:
    Wikilinks:
    Graph nodes:
    Graph edges:
    LINKS_TO edges:
    Vector collection:
    BM25 documents:

Verify the collection is:

    second_brain_vectors

---

# 22. PHASE 17 — SECOND BRAIN END-TO-END TEST

Test all three retrieval categories.

## Direct lookup

Example:

    What is CampusHub?

## Cross-reference

Example:

    How does CampusHub relate to the other projects in my knowledge base?

## Synthesis

Example:

    What recurring engineering patterns appear across my projects?

Answers must be grounded in the actual Second Brain corpus.

Do not fabricate facts.

---

# 23. PHASE 18 — EXAM PREP MATERIAL CHECKPOINT

If Exam Prep material has not been supplied:

    STOP

Ask the human:

    Please provide the local directory containing the Exam Prep /
    Newton School materials.

Supported:

    PDF
    DOCX
    TXT

Do not require the human to reorganize the files.

---

# 24. PHASE 19 — EXAM PREP INGESTION

Once the source directory is known:

    PYTHONPATH=. python rebuild_knowledge_graph.py --domain exam_prep

or the actual equivalent discovered in the repository.

Verify:

    exam_prep_vectors

and:

    data/exam_prep_knowledge_graph.json

are populated.

Report:

    Documents:
    Chunks:
    Entities:
    Graph nodes:
    Graph edges:
    BM25 documents:

---

# 25. PHASE 20 — CROSS-DOMAIN ISOLATION TEST

This test is mandatory.

Create unique markers:

    SECOND_BRAIN_UNIQUE_MARKER
    EXAM_PREP_UNIQUE_MARKER

or use distinctive real source phrases.

Verify:

    Second Brain query
        cannot retrieve Exam Prep marker

and:

    Exam Prep query
        cannot retrieve Second Brain marker

Test isolation at:

    - vector retrieval
    - BM25 retrieval
    - graph retrieval
    - final retrieval context
    - API
    - UI

If any layer leaks cross-domain data:

    STATUS: FAILED

Do not proceed until fixed.

---

# 26. PHASE 21 — BENCHMARK DATA

Create:

    synapse/data/benchmarks/

with:

    qa_pairs_second_brain.json
    qa_pairs_exam_prep.json

Each must contain:

    15–20 questions.

Question categories:

    Direct Lookup
    Cross-Reference
    Synthesis

Suggested distribution:

    5–7 direct lookup
    5–7 cross-reference
    5–7 synthesis

Adjust to remain within 15–20 total.

---

# 27. PHASE 22 — SECOND BRAIN BENCHMARK

Generate questions ONLY from actual Second Brain content.

Do not invent facts.

Examples:

    What is the purpose of CampusHub?

    How does CampusHub relate to another project?

    What engineering patterns repeat across my projects?

Expected answers must be grounded in actual source material.

---

# 28. PHASE 23 — EXAM PREP BENCHMARK

Generate questions from actual Exam Prep material.

Use:

    Direct Lookup
    Cross-Reference
    Synthesis

Examples:

    What is X?

    How are X and Y related?

    Which concepts recur across these materials?

Expected answers must be grounded in the actual coursework.

---

# 29. PHASE 24 — BENCHMARK HARNESS

Inspect:

    run_benchmark_now.py

If it lacks:

    --domain

implement it.

Required:

    PYTHONPATH=. python run_benchmark_now.py --domain second_brain

and:

    PYTHONPATH=. python run_benchmark_now.py --domain exam_prep

The same retrieval pipeline must be used for both.

Only domain configuration/data should change.

---

# 30. PHASE 25 — BENCHMARK OUTPUT

Generate:

    benchmark-results/
    ├── second_brain.json
    ├── exam_prep.json
    └── summary.md

Where supported, report:

    Recall@5
    MRR
    accuracy
    latency
    retrieval success

Never fabricate metrics.

If a metric is unavailable:

    N/A — not implemented

rather than inventing a value.

---

# 31. PHASE 26 — REGRESSION TEST SUITE

Create or extend tests for:

    DomainProfile loading
    vector isolation
    graph isolation
    wikilink extraction
    LINKS_TO edges
    BM25 isolation
    query routing
    API domain routing
    benchmark domain routing
    ingestion
    Second Brain retrieval
    Exam Prep retrieval

Run:

    pytest

Also run:

    python -m compileall src

and any repository-specific test/lint/type-check commands.

---

# 32. PHASE 27 — SECOND BRAIN AGENT REGRESSION TEST

Test the full librarian workflow:

    raw/
      ↓
    Agent
      ↓
    approval
      ↓
    wiki/
      ↓
    indexes
      ↓
    wikilinks

Verify:

    - raw remains untouched
    - wiki is updated
    - master index is updated
    - topic index is updated
    - links are created
    - no destructive writes occur

---

# 33. PHASE 28 — CONTINUOUS SECOND BRAIN WORKFLOW

The intended ongoing workflow is:

    New note
       ↓
    raw/
       ↓
    Agent compile
       ↓
    wiki/
       ↓
    Synapse re-ingestion
       ↓
    Retrieval becomes current

The system should document this workflow.

Do not automatically ingest raw notes directly into Synapse.

Synapse should retrieve from the processed wiki.

---

# 34. PHASE 29 — OPTIONAL AUTOMATION

If safe and practical, create a command such as:

    ./scripts/compile-and-ingest-second-brain.sh

which performs:

    Agent compilation
       ↓
    wiki audit
       ↓
    Second Brain ingestion
       ↓
    validation

Do not make this destructive.

If Agent TUI requires interactive human approval, preserve that step.

---

# 35. PHASE 30 — README REWRITE

Rewrite:

    synapse/README.md

The README must no longer frame Synapse purely as an industrial corpus demo.

Start with the dual-domain proposition:

    One hybrid retrieval engine, two live personal domains —
    a Second Brain built on the Obsidian + Claude Code pattern,
    and an Exam Prep assistant over my own coursework.
    Swap the domain config, not the code.

Then include:

    1. Benchmark results
    2. Problem
    3. Architecture
    4. Domain profiles
    5. Second Brain
    6. Exam Prep
    7. Wikilink graph
    8. Hybrid retrieval
    9. Why Synapse instead of only Obsidian/Claude Code
    10. Installation
    11. Configuration
    12. Running locally
    13. Benchmarking
    14. Deployment

Keep existing useful architecture material.

Keep the industrial domain if already supported.

Do not delete it merely to simplify the README.

---

# 36. PHASE 31 — ARCHITECTURE DOCUMENTATION

Document:

    One engine
    Many domains

Show:

                         Domain Profile
                              │
              ┌───────────────┴───────────────┐
              │                               │
        Second Brain                      Exam Prep
              │                               │
        Markdown wiki                    PDF/DOCX/TXT
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
                          Reranking
                              │
                            Answer

Make it explicit that domain configuration changes:

    source
    entity types
    link syntax
    storage namespace
    chunk settings

not the fundamental retrieval architecture.

---

# 37. PHASE 32 — DEPLOYMENT READINESS

Inspect:

    Dockerfile
    start.sh
    requirements.txt
    environment configuration

Ensure local startup works before deployment.

The target deployment class is a stateful application environment such as:

    Railway
    or
    Render

Do not target a serverless-only architecture that cannot persist the required
data.

---

# 38. PHASE 33 — PERSISTENT STORAGE

Production must persist:

    data/chroma_db
    data/*.json

Configure persistent volumes where required.

Verify that restarting the service does not erase:

    vector collections
    graph data

---

# 39. PHASE 34 — ENVIRONMENT VARIABLES

Audit all environment variables.

Create/update:

    .env.example

Never commit:

    API keys
    tokens
    passwords
    private credentials

Document:

    variable name
    purpose
    required/optional
    example format

but never include real secrets.

---

# 40. PHASE 35 — DEPLOYMENT HUMAN CHECKPOINT

Stop only when human credentials/configuration are required.

Ask for:

    deployment provider
    production source-path strategy
    required environment variables
    API credentials through secure configuration

Do not ask the human to paste secrets into repository files.

---

# 41. PHASE 36 — PRODUCTION SMOKE TEST

After deployment test:

    /health

Then:

    Second Brain query

Then:

    Exam Prep query

Then switch the UI domain.

Verify:

    Second Brain
        → Second Brain results

    Exam Prep
        → Exam Prep results

Verify graph visualization changes accordingly.

---

# 42. PHASE 37 — RESTART PERSISTENCE TEST

Restart the deployed service.

Then verify:

    Second Brain collection still exists
    Exam Prep collection still exists
    Second Brain graph still exists
    Exam Prep graph still exists

If data disappears:

    STATUS: FAILED

Do not declare deployment complete.

---

# 43. PHASE 38 — FINAL END-TO-END TEST

Run:

    Second Brain raw note
        ↓
    Agent compilation
        ↓
    wiki article
        ↓
    wikilinks
        ↓
    Synapse ingestion
        ↓
    vector
        ↓
    BM25
        ↓
    graph
        ↓
    retrieval
        ↓
    reranking
        ↓
    answer

Then:

    Exam Prep material
        ↓
    ingestion
        ↓
    exam_prep vector
        ↓
    exam_prep BM25
        ↓
    exam_prep graph
        ↓
    retrieval
        ↓
    answer

Then:

    cross-domain isolation test

---

# 44. PHASE 39 — FINAL ACCEPTANCE CRITERIA

The system is COMPLETE only when every applicable item passes.

## Second Brain

    [ ] Agent TUI works
    [ ] Agent reads vault
    [ ] Agent approval workflow works
    [ ] Approved writes work
    [ ] raw/ preserved
    [ ] wiki/ compiled
    [ ] topic indexes exist
    [ ] master index updated
    [ ] wikilinks exist
    [ ] wiki audit completed

## Synapse

    [ ] DomainProfile works
    [ ] Second Brain profile works
    [ ] Exam Prep profile works
    [ ] separate vector collections
    [ ] separate graphs
    [ ] BM25 domain-aware
    [ ] query engine domain-aware
    [ ] API domain-aware
    [ ] UI domain-aware
    [ ] wikilinks create LINKS_TO edges

## Retrieval

    [ ] Second Brain ingestion works
    [ ] Exam Prep ingestion works
    [ ] direct lookup works
    [ ] cross-reference works
    [ ] synthesis works
    [ ] graph retrieval works
    [ ] reranking works where configured
    [ ] domain isolation passes

## Evaluation

    [ ] Second Brain benchmark exists
    [ ] Exam Prep benchmark exists
    [ ] 15–20 questions/domain
    [ ] --domain benchmark support
    [ ] real metrics generated
    [ ] benchmark results documented

## Documentation

    [ ] README rewritten
    [ ] architecture documented
    [ ] setup documented
    [ ] domain configuration documented
    [ ] benchmark commands documented
    [ ] deployment documented
    [ ] .env.example updated

## Deployment

    [ ] Docker build succeeds
    [ ] application starts
    [ ] persistent storage configured
    [ ] environment variables configured
    [ ] health endpoint works
    [ ] Second Brain works
    [ ] Exam Prep works
    [ ] domain switching works
    [ ] restart persistence works

---

# 45. FINAL REPORT

Create:

    PROJECT_COMPLETION_REPORT.md

Use:

    # ADHD-CURE Project Completion Report

    ## Overall Status

    COMPLETE / PARTIAL / BLOCKED

    ## Workspace

    Components:
    Synapse:
    Second Brain:
    Agent TUI:

    ## Second Brain

    Raw files:
    Topics:
    Articles:
    Wikilinks:
    Graph nodes:
    Graph edges:

    ## Exam Prep

    Documents:
    Chunks:
    Entities:
    Graph nodes:
    Graph edges:

    ## Retrieval

    Second Brain:
    Direct lookup:
    Cross-reference:
    Synthesis:

    Exam Prep:
    Direct lookup:
    Cross-reference:
    Synthesis:

    ## Isolation

    Vector:
    BM25:
    Graph:
    API:
    UI:

    ## Tests

    Passed:
    Failed:
    Skipped:

    ## Benchmarks

    Second Brain:
    Exam Prep:

    ## Deployment

    Provider:
    URL:
    Health:
    Persistence:

    ## Human Actions Required

    <only genuine remaining actions>

    ## Known Limitations

    <only verified limitations>

---

# 46. EXECUTION ORDER

The agent MUST execute in this order:

    1. Workspace discovery
    2. Agent TUI approval fix
    3. Agent TUI tests
    4. Second Brain compilation
    5. Second Brain audit
    6. Synapse domain audit
    7. Domain profiles
    8. Vector isolation
    9. Graph isolation
    10. Wikilink extraction
    11. LINKS_TO verification
    12. BM25 domain isolation
    13. Query pipeline audit
    14. Streamlit domain selector
    15. FastAPI domain selection
    16. Second Brain ingestion
    17. Second Brain retrieval tests
    18. Request Exam Prep source if needed
    19. Exam Prep ingestion
    20. Exam Prep retrieval tests
    21. Cross-domain isolation
    22. Benchmark generation
    23. Benchmark harness
    24. Regression tests
    25. README
    26. Architecture docs
    27. Deployment preparation
    28. Production deployment
    29. Smoke test
    30. Restart persistence test
    31. Final end-to-end test
    32. Final completion report

Do not skip checkpoints.

---

# 47. CHECKPOINT POLICY

After every major phase print:

    ==================================================
    CHECKPOINT
    ==================================================

    Phase:
    Status: PASS / FAIL / BLOCKED

    What changed:
    ...

    Tests:
    ...

    Evidence:
    ...

    Human action:
    NONE / <specific action>

    Next phase:
    ...

    ==================================================

Do not continue past a FAILED checkpoint.

A BLOCKED checkpoint may be bypassed only for unrelated work.

---

# 48. CODE QUALITY POLICY

Prefer:

    small changes
    clear interfaces
    domain-aware dependency passing
    reusable components
    tests
    backwards compatibility

Avoid:

    global mutable state
    hidden domain defaults
    duplicated pipelines
    unnecessary abstractions
    massive rewrites
    hardcoded user paths
    secrets in source
    fake benchmark values

---

# 49. DOMAIN ISOLATION IS THE CORE REQUIREMENT

The following must always remain independent:

    SECOND BRAIN

    collection:
        second_brain_vectors

    graph:
        second_brain_knowledge_graph.json

    source:
        second-brain/wiki


    EXAM PREP

    collection:
        exam_prep_vectors

    graph:
        exam_prep_knowledge_graph.json

    source:
        configured exam material directory

BM25 must also remain domain-specific.

The shared retrieval engine is allowed.

The shared data namespace is not.

---

# 50. IMPORTANT: DO NOT OVER-ENGINEER

The objective is not to create a massive framework.

The objective is:

    reliable
    explainable
    testable
    domain-aware
    local-first
    practical

The system should remain understandable by one developer.

If a simple solution satisfies the requirements, prefer it.

---

# 51. IMPORTANT: SECOND BRAIN SOURCE OF TRUTH

The hierarchy is:

    Human source material
            ↓
        raw/
            ↓
    Agent compilation
            ↓
        wiki/
            ↓
        Synapse

Synapse is NOT the authoritative knowledge store.

The Obsidian wiki is.

If Synapse's index becomes stale:

    re-ingest

Do not edit Synapse's stored chunks manually to "fix" knowledge.

---

# 52. IMPORTANT: SYNTHESIS LOOP

The long-term Second Brain workflow may support:

    query
      ↓
    retrieve wiki
      ↓
    synthesize
      ↓
    save synthesis as new wiki article
      ↓
    add wikilinks
      ↓
    update indexes
      ↓
    re-ingest

If implementing this workflow, preserve human approval for writes.

Do not automatically mutate the knowledge base during a read-only query.

---

# 53. FINAL DEFINITION OF DONE

The project is considered finished only when:

    The Agent can organize the Second Brain.

    The Second Brain can be ingested by Synapse.

    Synapse can retrieve the Second Brain.

    Synapse can retrieve Exam Prep.

    Both domains use the same retrieval engine.

    Their vector stores are isolated.

    Their BM25 indexes are isolated.

    Their graphs are isolated.

    Wikilinks become graph relationships.

    The UI can switch domains.

    The API can select domains.

    Both domains have benchmark suites.

    Cross-domain leakage tests pass.

    The system survives restart.

    Documentation explains the architecture.

    Production deployment works.

If any of these are not verified:

    PARTIALLY COMPLETE

not:

    COMPLETE

---

# 54. START NOW

Begin with:

    PHASE 0 — WORKSPACE DISCOVERY

Do not ask the human what to do first.

Inspect the workspace and proceed autonomously.

Only stop when a genuine human decision, private source, credential,
or semantic judgment is required.

The objective is not to merely create files.

The objective is to produce a working:

    Second Brain
        +
    Agent Librarian
        +
    Dual-Domain Synapse
        +
    Exam Prep Engine
        +
    Benchmarked Retrieval System
        +
    Deployable Application

END OF MASTER BUILD MANUAL