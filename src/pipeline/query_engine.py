"""Query Engine — context retrieval + answer generation.

Public API
----------
retrieve_context(query, top_k, collection_name)
    Embeds the query, searches ChromaDB for top_k chunks, extracts entities with
    spaCy/regex, traverses the NetworkX knowledge graph 1-hop per entity, and
    returns a merged, deduplicated context dict:
        {vector_chunks: [...], graph_entities: [...], graph_relations: [...]}

generate_answer(query, context)
    Builds a structured RAG prompt from the context object, calls the local LLM
    (Ollama if running, otherwise smart-fallback), and safe-parses the required
    JSON response:
        {answer: str, sources: [{doc_id, excerpt}], confidence: float,
         entities_used: [str], key_points: [str]}

The module does NOT call the Claude API — it uses Ollama (local, no API key).
To enable LLM answers: install Ollama (https://ollama.com) and run
  ollama pull llama3.2 && ollama serve
"""

import json
import copy
from typing import Dict, Any, List, Optional
from loguru import logger
import numpy as np

from src.config import settings
from src.pipeline.embedder import TextEmbedder
from src.storage.chroma_store import VectorStore
from src.pipeline.extractor import extract_entities
from src.graph.knowledge_graph import get_knowledge_graph
from src.pipeline.llm import get_llm, _extract_json, _smart_fallback
from src.pipeline.bm25_index import get_bm25_index

# Singletons for reusing instances across calls
_embedder: Optional[TextEmbedder] = None
_vector_store: Optional[VectorStore] = None
_cross_encoder: Optional[Any] = None

# Stop words for keyword extraction in re-ranking boost
_KEYWORD_STOP_WORDS = frozenset({
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
    'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
    'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
    'once', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'because',
    'but', 'and', 'or', 'if', 'while', 'about', 'against', 'that', 'this',
    'these', 'those', 'what', 'which', 'who', 'whom',
})


class SemanticCache:
    """Persistent rolling cache for semantic similarity search over recent queries."""

    def __init__(self, max_size: int = 500, threshold: float = 0.95):
        self.max_size = max_size
        self.threshold = threshold
        self.cache = []
        self.cache_path = settings.data_dir / "semantic_cache.json"
        self._load_cache()

    def _load_cache(self):
        """Load cache entries from local JSON file."""
        try:
            if self.cache_path.exists():
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        self.cache.append({
                            "embedding": np.array(item["embedding"]),
                            "answer": item["answer"]
                        })
                logger.info(f"Semantic Cache: Loaded {len(self.cache)} entries from {self.cache_path}")
        except Exception as e:
            logger.error(f"Semantic Cache: Failed to load cache from disk: {e}")

    def _save_cache(self):
        """Save cache entries to local JSON file."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            serializable_cache = []
            for entry in self.cache:
                serializable_cache.append({
                    "embedding": entry["embedding"].tolist(),
                    "answer": entry["answer"]
                })
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(serializable_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Semantic Cache: Failed to save cache to disk: {e}")

    def get(self, query_embedding: np.ndarray) -> Optional[Dict[str, Any]]:
        if not self.cache or query_embedding is None:
            return None

        # Normalize query embedding
        q_norm = np.linalg.norm(query_embedding)
        if q_norm == 0:
            return None
        q_emb = query_embedding / q_norm

        best_similarity = -1.0
        best_answer = None

        for entry in self.cache:
            entry_emb = entry["embedding"]
            e_norm = np.linalg.norm(entry_emb)
            if e_norm == 0:
                continue
            e_emb = entry_emb / e_norm

            similarity = float(np.dot(q_emb, e_emb))
            if similarity > best_similarity:
                best_similarity = similarity
                best_answer = entry["answer"]

        if best_similarity >= self.threshold:
            logger.info(f"Semantic Cache HIT: similarity = {best_similarity:.4f} (>= {self.threshold})")
            return best_answer

        logger.debug(f"Semantic Cache MISS: best similarity = {best_similarity:.4f} (< {self.threshold})")
        return None

    def set(self, query_embedding: np.ndarray, answer: Dict[str, Any]):
        if query_embedding is None or answer is None:
            return

        # Simple rolling FIFO eviction to act as a cache of max size
        if len(self.cache) >= self.max_size:
            self.cache.pop(0)

        # Store a deep copy of the answer to prevent modification
        self.cache.append({
            "embedding": query_embedding.copy(),
            "answer": copy.deepcopy(answer)
        })
        logger.debug(f"Cached answer in semantic cache. Cache size: {len(self.cache)}/{self.max_size}")
        self._save_cache()


_semantic_cache = SemanticCache(max_size=500, threshold=0.95)


def get_embedder() -> TextEmbedder:
    """Get or create the text embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedder()
    return _embedder


def get_vector_store(collection_name: str = None) -> VectorStore:
    """Get or create the vector store instance for the specified collection."""
    global _vector_store
    name = collection_name or settings.chroma_collection
    if _vector_store is None or _vector_store.collection_name != name:
        _vector_store = VectorStore(collection_name=name)
    return _vector_store


def get_cross_encoder() -> Any:
    """Get or create the cross-encoder instance for re-ranking."""
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        logger.info("Loading CrossEncoder: cross-encoder/ms-marco-MiniLM-L-6-v2")
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def init_bm25_index_lazy():
    """Lazily load all documents from ChromaDB and build the BM25 index if not already built."""
    index = get_bm25_index()
    if index.bm25 is None:
        logger.info("BM25Index: Lazily building index from ChromaDB...")
        try:
            store = get_vector_store()
            all_chunks = store.collection.get(include=["documents"])
            c_ids = all_chunks.get("ids", [])
            documents = all_chunks.get("documents", [])
            chunks_list = []
            for i in range(len(c_ids)):
                chunks_list.append({
                    "id": c_ids[i],
                    "text": documents[i]
                })
            index.build(chunks_list)
        except Exception as e:
            logger.error(f"BM25Index: Failed to build index lazily: {e}")


def retrieve_context(query: str, top_k: int = 5, collection_name: str = None, filters: dict = None) -> Dict[str, Any]:
    """Retrieve and merge context from ChromaDB (vector) and NetworkX (graph).

    Args:
        query: The natural language search query.
        top_k: Number of chunks to retrieve from the vector store.
        collection_name: ChromaDB collection to search against.
        filters: Metadata filters to restrict retrieval.

    Returns:
        A dictionary with merged and deduplicated context:
        {
            "vector_chunks": [
                {
                    "chunk_id": str,
                    "text": str,
                    "metadata": dict,
                    "distance": float
                },
                ...
            ],
            "graph_entities": [
                {
                    "id": str,
                    "type": str
                },
                ...
            ],
            "graph_relations": [
                {
                    "source": str,
                    "target": str,
                    "relation": str
                },
                ...
            ]
        }
    """
    logger.info(f"Retrieving context for query: '{query}' with filters: {filters}")

    # Lazily initialize BM25 index and compute scores
    init_bm25_index_lazy()
    bm25_index = get_bm25_index()
    bm25_scores = bm25_index.get_scores(query)

    # 1. Embed the query and retrieve top_k chunks from ChromaDB (diverse search)
    embedder = get_embedder()
    store = get_vector_store(collection_name)
    
    query_embedding = embedder.embed_query(query)
    
    # Pull top_k=10 chunks from ChromaDB instead of 3 by default, or respect top_k parameter
    n_part = max(10, top_k)
    
    if filters:
        where_reg = {"$and": [{"record_type": {"$in": ["txt", "pdf", "docx"]}}, filters]}
        where_csv = {"$and": [{"record_type": {"$nin": ["txt", "pdf", "docx"]}}, filters]}
    else:
        where_reg = {"record_type": {"$in": ["txt", "pdf", "docx"]}}
        where_csv = {"record_type": {"$nin": ["txt", "pdf", "docx"]}}

    reg_results = store.query(query_embedding, n_results=n_part, where=where_reg)
    csv_results = store.query(query_embedding, n_results=n_part, where=where_csv)

    vector_chunks = []
    for search_results in [reg_results, csv_results]:
        if search_results and search_results["documents"] and len(search_results["documents"][0]) > 0:
            for i in range(len(search_results["documents"][0])):
                chunk_id = search_results["ids"][0][i]
                text = search_results["documents"][0][i]
                metadata = search_results["metadatas"][0][i]
                distance = search_results["distances"][0][i]
                vector_chunks.append({
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata,
                    "distance": distance
                })
    
    # Normalization and BM25 + Vector Hybrid Fusion (hybrid disabled for the
    # vector-only ablation configuration)
    if vector_chunks:
        if settings.use_hybrid:
            chunk_bm25_scores = [bm25_scores.get(c["chunk_id"], 0.0) for c in vector_chunks]
            max_bm25 = max(chunk_bm25_scores) if chunk_bm25_scores else 0.0

            alpha = 0.4
            for c in vector_chunks:
                # Preserving absolute cosine similarity range [0, 1]
                norm_vector = max(0.0, min(1.0, 1.0 - c["distance"]))

                b_score = bm25_scores.get(c["chunk_id"], 0.0)
                norm_bm25 = b_score / max_bm25 if max_bm25 > 0 else 0.0

                c["hybrid_score"] = alpha * norm_bm25 + (1 - alpha) * norm_vector

            # Sort by hybrid score and keep top 16 candidates for re-ranking
            vector_chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)
        else:
            # Pure vector ranking: sort by distance ascending
            for c in vector_chunks:
                c["hybrid_score"] = max(0.0, min(1.0, 1.0 - c["distance"]))
            vector_chunks.sort(key=lambda x: x["distance"])

        vector_chunks = vector_chunks[:16]

    # Re-rank chunks locally using CrossEncoder (disabled for the no-reranker
    # ablation configurations)
    if vector_chunks:
        if settings.use_reranker:
            try:
                cross_encoder = get_cross_encoder()
                pairs = [[query, c["text"]] for c in vector_chunks]
                scores = cross_encoder.predict(pairs)

                # Extract meaningful keywords from query for keyword matching boost
                query_lower = query.lower()
                query_keywords = [w for w in query_lower.split() if len(w) > 3 and w not in _KEYWORD_STOP_WORDS]

                for idx, score in enumerate(scores):
                    is_csv = vector_chunks[idx]["metadata"].get("record_type") not in ["txt", "pdf", "docx"]
                    boost = 0.0 if is_csv else 8.0

                    # Keyword matching boost for regulatory documents
                    keyword_boost = 0.0
                    if not is_csv and query_keywords:
                        chunk_text_lower = vector_chunks[idx]["text"].lower()
                        keyword_matches = sum(1 for kw in query_keywords if kw in chunk_text_lower)
                        keyword_boost = min(12.0, keyword_matches * 3.0)  # Up to 12 points for keyword matches

                    vector_chunks[idx]["cross_score"] = float(score)
                    vector_chunks[idx]["combined_score"] = float(score) + 15.0 * vector_chunks[idx]["hybrid_score"] + boost + keyword_boost
                vector_chunks.sort(key=lambda x: x["combined_score"], reverse=True)
                logger.debug("Successfully re-ranked vector chunks using CrossEncoder with hybrid score fusion + keyword boost")
            except Exception as e:
                logger.error(f"Failed to re-rank chunks: {e}. Falling back to hybrid score.")
                vector_chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)
        else:
            # Ablation: skip the cross-encoder, keep the hybrid/distance ranking
            vector_chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)

        # Expose the full ranked candidate list for benchmark retrieval metrics
        candidate_chunks = vector_chunks[:]
        # Keep only the top 3 chunks for context assembly
        vector_chunks = vector_chunks[:3]
    else:
        candidate_chunks = []

    logger.debug(f"Retrieved {len(vector_chunks)} vector chunks (diverse search) from collection '{store.collection_name}'")

    # 2. Extract entities and traverse the knowledge graph (skipped entirely for
    #    the no-graph ablation configuration)
    graph_entities_list = []
    graph_relations_list = []
    if settings.use_graph:
        try:
            extracted_entities = extract_entities(query)
        except Exception as e:
            logger.error(f"Entity extraction failed for query '{query[:100]}': {e}. Continuing without query entities.")
            extracted_entities = {}

        # Flatten and deduplicate all query entities
        query_entity_ids = set()
        for category, entities in extracted_entities.items():
            for entity in entities:
                query_entity_ids.add(entity)

        # 2b. Also extract entity IDs from retrieved chunk metadata (Tier 1.1)
        for chunk in vector_chunks:
            entity_ids_json = chunk["metadata"].get("entity_ids", "[]")
            try:
                chunk_entity_ids = json.loads(entity_ids_json) if isinstance(entity_ids_json, str) else entity_ids_json
                for eid in chunk_entity_ids:
                    if eid:
                        query_entity_ids.add(eid)
            except (json.JSONDecodeError, TypeError):
                pass

        logger.debug(f"Total entities for graph traversal: {len(query_entity_ids)} (from query + chunk metadata)")

        MAX_GRAPH_ENTITIES = 20
        if len(query_entity_ids) > MAX_GRAPH_ENTITIES:
            chunk_eids = set()
            for c in vector_chunks:
                entity_ids_json = c["metadata"].get("entity_ids", "[]")
                try:
                    chunk_entity_ids = json.loads(entity_ids_json) if isinstance(entity_ids_json, str) else entity_ids_json
                    for eid in chunk_entity_ids:
                        if isinstance(eid, str):
                            chunk_eids.add(eid)
                except Exception:
                    pass
            query_only = [e for e in query_entity_ids if e not in chunk_eids]
            chunk_only = [e for e in query_entity_ids if e not in query_only]
            query_entity_ids = set(query_only + chunk_only[:MAX_GRAPH_ENTITIES - len(query_only)])
            logger.debug(f"Capped to {len(query_entity_ids)} entities for graph traversal")

        # 3. Traverse the NetworkX graph 1-hop for each found entity
        kg = get_knowledge_graph()

        for entity in query_entity_ids:
            # Check if node exists in NetworkX graph
            if kg.graph.has_node(entity):
                # Include the queried node itself
                graph_entities_list.append({
                    "id": entity,
                    "type": kg.graph.nodes[entity].get("type", "unknown")
                })

                # Traverse 1-hop neighbors
                for neighbor in kg.graph.neighbors(entity):
                    # Add neighbor node
                    graph_entities_list.append({
                        "id": neighbor,
                        "type": kg.graph.nodes[neighbor].get("type", "unknown")
                    })

                    # Add relationship edge
                    edge_data = kg.graph.edges[entity, neighbor]
                    graph_relations_list.append({
                        "source": entity,
                        "target": neighbor,
                        "relation": edge_data.get("relation", "related_to")
                    })

    # 4. Deduplicate graph nodes and edges
    # Deduplicate entities by 'id'
    seen_entities = set()
    deduped_entities = []
    for ent in graph_entities_list:
        if ent["id"] not in seen_entities:
            seen_entities.add(ent["id"])
            deduped_entities.append(ent)

    # Deduplicate relations (sorting source/target to treat undirected edges as identical)
    seen_relations = set()
    deduped_relations = []
    for rel in graph_relations_list:
        edge_key = (
            min(rel["source"], rel["target"]),
            max(rel["source"], rel["target"]),
            rel["relation"]
        )
        if edge_key not in seen_relations:
            seen_relations.add(edge_key)
            deduped_relations.append(rel)

    logger.debug(f"Traversed graph: found {len(deduped_entities)} entities and {len(deduped_relations)} relations")

    return {
        "vector_chunks": vector_chunks,
        "candidate_chunks": candidate_chunks,
        "graph_entities": deduped_entities,
        "graph_relations": deduped_relations
    }


# ── Answer generation ──────────────────────────────────────────────────────────

# Confidence guidance injected into the prompt so the LLM scores it consistently.
_CONFIDENCE_GUIDE = """
Confidence scoring rules (follow strictly — do NOT invent a number):
  High   (0.80-1.00) → direct, clear answer present in ≥2 document sources
  Medium (0.50-0.79) → partial information or only 1 source found, or no graph entities
  Low    (0.00-0.49) → context is empty, off-topic, or graph returned nothing

Hint for this specific query:
  vector_chunks retrieved: {n_chunks}
  graph entities matched : {n_entities}
  graph relations found  : {n_relations}
"""

_RAG_TEMPLATE = """
You are Synapse, an AI-powered knowledge intelligence assistant. Answer ONLY using the retrieved
context below. Never fabricate facts. 
CRITICAL: Keep your final JSON response extremely concise (under 150 tokens total) to prevent truncation.

=== DOCUMENT CONTEXT ===
{doc_context}

=== KNOWLEDGE GRAPH RELATIONSHIPS ===
{graph_context}

=== QUESTION ===
{question}

{confidence_guide}

Respond with ONLY this JSON object — no markdown fences, no preamble, no trailing text:
{{"answer": "<concise answer citing [Source N] labels, max 2 sentences>",
  "sources": [{{"doc_id": "<doc_id>", "excerpt": "<very short excerpt, max 8 words>"}}],
  "confidence": <float 0.0-1.0>,
  "entities_used": ["<entity IDs mentioned>"],
  "key_points": ["<short key point 1, max 8 words>", "<short key point 2, max 8 words>"]}}
"""


def classify_query_complexity(query: str, chunks: list) -> dict:
    """Shared heuristic complexity classifier for gating LLM thinking mode.

    Returns a dict with:
        enable_thinking (bool)
        reasoning_budget (int)
        is_complex (bool)
    """
    enable_thinking = True
    reasoning_budget = 1024

    is_complex = len(query) > 180

    comparison_words = [
        "versus", "compare", "difference between", "difference", "vs", "comparison",
        "which", "list", "all", "each", "across"
    ]
    query_lower = query.lower()
    if not is_complex and any(word in query_lower for word in comparison_words):
        is_complex = True

    if not is_complex and len(chunks) >= 2:
        doc1 = chunks[0]["metadata"].get("doc_id") if chunks[0].get("metadata") else None
        doc2 = chunks[1]["metadata"].get("doc_id") if chunks[1].get("metadata") else None
        dist1 = chunks[0].get("distance", 0.0)
        dist2 = chunks[1].get("distance", 0.0)
        if doc1 and doc2 and doc1 != doc2 and abs(dist1 - dist2) < 0.12:
            is_complex = True

    if not is_complex:
        enable_thinking = False
        reasoning_budget = 0
        logger.info("Complexity classifier: simple query → enable_thinking=False, reasoning_budget=0 (fast-path)")
    else:
        logger.info("Complexity classifier: complex query → enable_thinking=True, reasoning_budget=1024")

    return {
        "enable_thinking": enable_thinking,
        "reasoning_budget": reasoning_budget,
        "is_complex": is_complex,
    }


def generate_answer(query: str, context: Dict[str, Any], routing_mode: str = "auto") -> Dict[str, Any]:
    """Generate a structured RAG answer from the context object produced by retrieve_context().

    Args:
        query:   The original user question.
        context: Output of retrieve_context() — must contain keys
                 vector_chunks, graph_entities, graph_relations.
        routing_mode: Manual override selection ('auto', 'fast', 'deep').

    Returns:
        A dict with:
          answer       (str)   — full markdown answer citing sources
          sources      (list)  — [{doc_id, excerpt}, ...]
          confidence   (float) — 0.0–1.0 computed from retrieval quality heuristics
          entities_used (list) — entity IDs from the graph traversal
          key_points   (list)  — bullet-point summaries
          model_used   (str)   — label for display (e.g. 'Ollama / llama3.2')
    """
    # ── Check semantic cache ──────────────────────────────────────────────────
    embedder = get_embedder()
    query_embedding = None
    if routing_mode == "auto" and settings.use_semantic_cache:
        try:
            query_embedding = np.array(embedder.embed_query(query))
            cached_res = _semantic_cache.get(query_embedding)
            if cached_res is not None:
                cached_copy = copy.deepcopy(cached_res)
                cached_copy["model_used"] = cached_copy.get("model_used", "") + " (Semantic Cache)"
                return cached_copy
        except Exception as e:
            logger.error(f"Semantic Cache check failed: {e}")
            query_embedding = None

    chunks   = context.get("vector_chunks", [])
    entities = context.get("graph_entities", [])
    relations = context.get("graph_relations", [])

    # ── Confidence heuristic (passed as guidance to the prompt) ──────────────
    n_chunks    = len(chunks)
    n_entities  = len(entities)
    n_relations = len(relations)

    # Baseline confidence from retrieval quality — LLM adjusts within this band
    if n_chunks >= 2 and n_entities >= 1:
        guidance_conf = "High   (0.80-1.00)"
    elif n_chunks >= 1 or n_entities >= 1:
        guidance_conf = "Medium (0.50-0.79)"
    else:
        guidance_conf = "Low    (0.00-0.49)"

    # ── Build numbered source context ─────────────────────────────────────────
    doc_parts: List[str] = []
    source_list: List[Dict] = []
    for i, c in enumerate(chunks, 1):
        doc_id  = c["metadata"].get("doc_id", c.get("chunk_id", "unknown"))
        text    = c["text"].strip()
        dist    = c.get("distance", 0.0)
        score   = round(1.0 - float(dist), 3)
        doc_parts.append(f"[Source {i}] {doc_id}  (relevance: {score})\n{text}")
        source_list.append({"doc_id": doc_id, "excerpt": text[:250]})

    doc_context  = "\n\n---\n\n".join(doc_parts) or "No documents retrieved."

    # ── Build graph context string ─────────────────────────────────────────────
    graph_lines: List[str] = []
    for rel in relations[:10]:
        graph_lines.append(
            f"  {rel['source']} --[{rel['relation']}]--> {rel['target']}"
        )
    if not graph_lines:
        graph_lines = ["  No knowledge-graph relationships found for this query."]
    graph_context = "\n".join(graph_lines)

    entity_ids = [e["id"] for e in entities]

    # ── Build prompt ──────────────────────────────────────────────────────────
    conf_guide = _CONFIDENCE_GUIDE.format(
        n_chunks=n_chunks,
        n_entities=n_entities,
        n_relations=n_relations,
    ) + f"  Suggested confidence band: {guidance_conf}"

    prompt = _RAG_TEMPLATE.format(
        doc_context=doc_context,
        graph_context=graph_context,
        question=query,
        confidence_guide=conf_guide,
    )

    # ── Determine Model and Reasoning Settings based on Routing Mode ──────────
    if routing_mode == "fast":
        target_model = "meta/llama-3.1-8b-instruct"
        enable_thinking = False
        reasoning_budget = 0
        logger.info("Routing override: fast answer -> model=meta/llama-3.1-8b-instruct, enable_thinking=False")
    elif routing_mode == "deep":
        target_model = "nvidia/nemotron-3-ultra-550b-a55b"
        enable_thinking = True
        reasoning_budget = 1024
        logger.info("Routing override: deep reasoning -> model=nvidia/nemotron-3-ultra-550b-a55b, enable_thinking=True")
    else:  # "auto"
        target_model = settings.nvidia_model
        complexity = classify_query_complexity(query, chunks)
        enable_thinking = complexity["enable_thinking"]
        reasoning_budget = complexity["reasoning_budget"]

    llm = get_llm()
    is_nvidia = "NvidiaLLM" in type(llm).__name__
    llm_label = "NVIDIA API" if is_nvidia else "Ollama"

    if llm.available:
        logger.info(f"generate_answer: calling {llm_label} [{target_model}]")
        try:
            if is_nvidia:
                tokens_limit = 2048 if enable_thinking else 1024
                raw = llm.generate(
                    prompt,
                    max_tokens=tokens_limit,
                    enable_thinking=enable_thinking,
                    reasoning_budget=reasoning_budget,
                    model=target_model
                )
            else:
                raw = llm.generate(prompt, max_tokens=settings.max_tokens)
            result = _extract_json(raw)
        except Exception as e:
            logger.error(f"{llm_label} call failed: {e}. Using smart fallback.")
            result = None
    else:
        result = None

    if result is None:
        logger.info("generate_answer: using smart-context fallback")
        # Reuse llm.py fallback, then convert to query_engine schema
        fb = _smart_fallback(query, [
            {"doc_id": c["metadata"].get("doc_id", ""),
             "text": c["text"],
             "citation": c["metadata"].get("doc_id", ""),
             "distance": c.get("distance", 0.0)}
            for c in chunks
        ], graph_lines)
        result = fb
        result["confidence"] = 0.5 if chunks else 0.2
        result["sources"] = source_list
        result["model_used"] = "Smart Context"
        result["entities_used"] = entity_ids
        return result

    # ── Normalise output schema ───────────────────────────────────────────────
    # Ensure confidence is a float
    raw_conf = result.get("confidence", 0.5)
    if isinstance(raw_conf, str):
        # LLM returned "High" / "Medium" / "Low" — map to float
        raw_conf = {"high": 0.85, "medium": 0.60, "low": 0.25}.get(
            raw_conf.lower(), 0.5
        )
    result["confidence"] = round(float(raw_conf), 3)

    # Merge entity IDs from graph traversal into entities_used
    existing_ents = result.get("entities_used", result.get("entities_mentioned", []))
    result["entities_used"] = list(set(existing_ents + entity_ids))

    # Ensure sources list exists
    if not result.get("sources"):
        result["sources"] = source_list

    result.setdefault("key_points", [])
    result["model_used"] = (
        f"{llm_label} / {target_model}" if llm.available else "Smart Context"
    )

    if query_embedding is not None and routing_mode == "auto" and settings.use_semantic_cache and "Smart Context" not in result.get("model_used", ""):
        try:
            _semantic_cache.set(query_embedding, result)
        except Exception as e:
            logger.error(f"Failed to cache result: {e}")

    logger.info(
        f"generate_answer done — confidence={result['confidence']}, "
        f"model={result.get('model_used')}"
    )
    return result


if __name__ == "__main__":
    """
    Standalone smoke-test:
      PYTHONPATH=. python3 src/pipeline/query_engine.py
    Tests retrieve_context + generate_answer against 3 benchmark questions.
    """
    SAMPLE_QUERIES = [
        "Which equipment requires quarterly inspection?",
        "What permits are associated with PRM-2026-5001?",
        "What are the OISD-116 safety requirements for PUMP-A01?",
    ]

    print("=" * 70)
    print("Query Engine — retrieve_context + generate_answer smoke test")
    print("=" * 70)

    for i, q in enumerate(SAMPLE_QUERIES, 1):
        print(f"\n{'─'*60}")
        print(f"Q{i}: {q}")
        print("─" * 60)

        ctx = retrieve_context(q, top_k=5)
        print(
            f"  context → {len(ctx['vector_chunks'])} chunks, "
            f"{len(ctx['graph_entities'])} entities, "
            f"{len(ctx['graph_relations'])} relations"
        )

        ans = generate_answer(q, ctx)
        print(f"  confidence : {ans.get('confidence')}")
        print(f"  model      : {ans.get('model_used')}")
        print(f"  entities   : {ans.get('entities_used', [])[:4]}")
        print(f"  answer     : {str(ans.get('answer',''))[:200]}...")
        if ans.get("sources"):
            print(f"  sources    : {[s['doc_id'] for s in ans['sources'][:3]]}")
