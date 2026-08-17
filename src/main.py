"""Synapse — AI-Powered Knowledge Intelligence — Main API Application.

Day 4: Real LLM integration (Ollama, no API key), /benchmark/run, /feedback,
        /debug/search added.
"""

import copy
import json
import os
import shutil
import time

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import File, UploadFile, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger
import networkx as nx

from src.config import settings
from src.pipeline.ingest import IngestionPipeline
from src.pipeline.embedder import TextEmbedder
from src.pipeline.extractor import extract_entities
from src.pipeline.compliance import check_compliance
from src.pipeline.llm import get_llm, NvidiaLLM, OllamaLLM, _extract_json
from src.pipeline.query_engine import (
    retrieve_context, generate_answer, get_embedder,
    _RAG_TEMPLATE, _CONFIDENCE_GUIDE, _semantic_cache,
    classify_query_complexity, get_vector_store,
)
from src.storage.chroma_store import VectorStore
from src.graph.knowledge_graph import get_knowledge_graph
import numpy as np

# In-memory feedback store (persisted to disk on each write)
_FEEDBACK_FILE = settings.data_dir / "feedback.jsonl"

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG-powered industrial knowledge system with vector search + knowledge graph.",
)

# Serve static assets (e.g. bundled JS libraries)
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.isdir(_static_dir):
    static_app = StaticFiles(directory=str(_static_dir))
    static_app = CORSMiddleware(static_app, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.mount("/static", static_app, name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    logger.info("Pre-warming models and services...")
    try:
        get_embedder()
        get_vector_store()
        get_knowledge_graph()
        get_llm()
        logger.info("Pre-warming complete. All services ready.")
    except Exception as e:
        logger.error(f"Error during startup pre-warming: {e}")


class ComplianceRequest(BaseModel):
    """Schema for compliance check requests."""
    requirement: str
    top_k: Optional[int] = 10


class QueryRequest(BaseModel):
    """Schema for incoming RAG queries."""
    question: str = Field(..., min_length=1, max_length=1000, description="The query string")
    top_k: Optional[int] = Field(settings.top_k, ge=1, le=20)
    filters: Optional[dict] = None
    routing_mode: Optional[str] = Field("auto", description="Routing mode: 'auto', 'fast', or 'deep'")


class QueryResponse(BaseModel):
    """Schema for RAG query response (Day 4: includes LLM fields)."""
    answer: str
    sources: List[dict]
    confidence: Union[str, float]   # float 0.0-1.0 from query_engine, or 'High'/'Medium'/'Low'
    entities_used: List[str] = []
    key_points: List[str] = []
    model_used: str = "unknown"
    latency_ms: int = 0
    trace: Optional[dict] = None    # per-stage pipeline trace for the evidence panel


class FeedbackRequest(BaseModel):
    """Thumbs-up / thumbs-down on an answer."""
    question: str
    answer: str
    rating: int          # +1 = positive, -1 = negative
    comment: Optional[str] = None


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "version": settings.app_version}


@app.get("/robots.txt", response_class=Response)
async def robots_txt():
    """Serve robots.txt for search engines."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Sitemap: http://localhost:8000/sitemap.xml\n"
    )
    return Response(content=content, media_type="text/plain")


@app.get("/sitemap.xml", response_class=Response)
async def sitemap_xml():
    """Serve sitemap.xml for search engines."""
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        '    <loc>http://localhost:8501/</loc>\n'
        '    <changefreq>daily</changefreq>\n'
        '    <priority>1.0</priority>\n'
        '  </url>\n'
        '  <url>\n'
        '    <loc>http://localhost:8501/1_Knowledge_Explorer</loc>\n'
        '    <changefreq>daily</changefreq>\n'
        '    <priority>0.8</priority>\n'
        '  </url>\n'
        '</urlset>'
    )
    return Response(content=content, media_type="application/xml")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


# --- Compliance Check Endpoint ---

@app.post("/compliance/check")
async def compliance_check(request: ComplianceRequest):
    """Check a regulatory requirement against ingested procedures for gaps."""
    try:
        logger.info(f"Compliance check request: {request.requirement[:100]}...")
        result = check_compliance(request.requirement, top_k=request.top_k)
        return result
    except Exception as e:
        logger.error(f"Error during compliance check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Knowledge Graph Endpoints ---

@app.get("/graph")
async def get_graph(max_nodes: int = Query(default=500, le=2000)):
    """Get the full knowledge graph as nodes/edges JSON for visualization."""
    try:
        kg = get_knowledge_graph()
        return kg.to_json(max_nodes=max_nodes)
    except Exception as e:
        logger.error(f"Error fetching knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/search")
async def graph_search(
    q: str = Query(..., description="Search term to match against node IDs"),
    node_types: Optional[str] = Query(default=None, description="Comma-separated list of node types to filter by"),
    limit: int = Query(default=50, le=200, description="Max results to return")
):
    """Search for graph nodes by name/label."""
    try:
        kg = get_knowledge_graph()
        types_list = [t.strip() for t in node_types.split(",")] if node_types else None
        matches = kg.search_nodes(q, node_types=types_list, limit=limit)
        return {"query": q, "results": matches, "count": len(matches)}
    except Exception as e:
        logger.error(f"Error searching graph nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/node/{node_id}")
async def get_graph_node(node_id: str):
    """Get node metadata, immediate neighbors, and linked resource IDs."""
    try:
        kg = get_knowledge_graph()
        return kg.get_node_metadata(node_id)
    except Exception as e:
        logger.error(f"Error fetching node metadata for {node_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/top")
async def get_graph_top(
    n: int = Query(default=30, le=200, description="Number of top nodes to return"),
    node_types: Optional[str] = Query(default=None, description="Comma-separated list of node types to filter by")
):
    """Get top N most-connected nodes for initial graph loading."""
    try:
        kg = get_knowledge_graph()
        types_list = [t.strip() for t in node_types.split(",")] if node_types else None
        top_ids = kg.get_top_nodes(n=n, node_types=types_list)
        subgraph = kg.get_subgraph_for_nodes(top_ids)
        return subgraph
    except Exception as e:
        logger.error(f"Error fetching top graph nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/path")
async def graph_find_path(
    source: str = Query(..., description="Source entity ID"),
    target: str = Query(..., description="Target entity ID"),
):
    """Find shortest path between two entities in the knowledge graph."""
    try:
        kg = get_knowledge_graph()
        result = kg.find_path(source, target)
        if "error" in result and not result.get("path"):
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding path from {source} to {target}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/stats")
async def graph_stats():
    """Get detailed graph statistics for the dashboard."""
    try:
        kg = get_knowledge_graph()
        stats = kg.get_stats()
        # Add additional metrics
        stats["connected_components"] = (
            nx.number_connected_components(kg.graph)
            if kg.graph.number_of_nodes() > 0 else 0
        )
        # Average degree
        if kg.graph.number_of_nodes() > 0:
            degrees = [d for _, d in kg.graph.degree()]
            stats["avg_degree"] = round(sum(degrees) / len(degrees), 2)
            stats["max_degree"] = max(degrees)
        else:
            stats["avg_degree"] = 0
            stats["max_degree"] = 0
        return stats
    except Exception as e:
        logger.error(f"Error fetching graph stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@lru_cache(maxsize=128)
def _fetch_subgraph_cached(entity_id: str, depth: int) -> Optional[dict]:
    """Helper to fetch and format the subgraph, cached in-memory."""
    kg = get_knowledge_graph()
    raw = kg.get_entity_neighbors(entity_id, depth=depth)
    
    if "error" in raw:
        return None
        
    center_data = raw.get("center", {})
    center = {
        "id": center_data.get("id", entity_id),
        "label": center_data.get("id", entity_id),
        "type": center_data.get("type", "unknown")
    }
    
    neighbors = []
    edges = []
    
    for n in raw.get("neighbors", []):
        neighbors.append({
            "id": n.get("id"),
            "label": n.get("id"),
            "type": n.get("type", "unknown"),
            "relation": n.get("relation", "related_to")
        })
        edges.append({
            "source": n.get("source"),
            "target": n.get("id"),
            "relation_type": n.get("relation", "related_to")
        })
        
    return {
        "center": center,
        "neighbors": neighbors,
        "edges": edges
    }

@app.get("/graph/entity/{entity_id}")
async def get_entity_subgraph(entity_id: str, depth: int = Query(default=1, le=2)):
    """Get subgraph centered on one entity for frontend visualization."""
    try:
        subgraph = _fetch_subgraph_cached(entity_id, depth)
        if not subgraph:
            raise HTTPException(
                status_code=404, 
                detail=f"Entity '{entity_id}' not found in the knowledge graph. Check the ID."
            )
        return subgraph
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching entity subgraph for {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/entities")
async def get_entities():
    """List all extracted entities grouped by type."""
    try:
        kg = get_knowledge_graph()
        entities_by_type = kg.get_entities_by_type()
        stats = kg.get_stats()
        return {
            "entities": entities_by_type,
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Error fetching entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Ingestion Endpoints ---

SUPPORTED_EXTENSIONS = {".txt", ".csv", ".pdf", ".docx"}

@app.post("/ingest/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload and ingest one or more documents (PDF, DOCX, CSV, TXT)."""
    pipeline = IngestionPipeline()
    temp_dir = settings.data_dir / "temp_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        store = get_vector_store()
        existing_docs = store.collection.get(include=["metadatas"])
        existing_filenames = set()
        if existing_docs and existing_docs.get("metadatas"):
            for meta in existing_docs["metadatas"]:
                if meta and "doc_id" in meta:
                    existing_filenames.add(meta["doc_id"])
    except Exception as e:
        logger.warning(f"Failed to fetch existing documents for duplicate check: {e}")
        existing_filenames = set()
    
    results = []
    for file in files:
        safe_filename = Path(file.filename).name
        ext = Path(safe_filename).suffix.lower()
        
        if ext not in SUPPORTED_EXTENSIONS:
            results.append({
                "doc_id": safe_filename, 
                "status": "error", 
                "error": f"Unsupported file type: '{ext}'. Allowed: {', '.join(SUPPORTED_EXTENSIONS)}"
            })
            continue
            
        if safe_filename in existing_filenames:
            results.append({
                "doc_id": safe_filename, 
                "status": "error", 
                "error": "Duplicate upload. A document with this filename is already indexed."
            })
            continue

        temp_file_path = temp_dir / safe_filename
        try:
            # Save file temporarily to disk
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            if temp_file_path.stat().st_size == 0:
                raise ValueError("File is empty or corrupted.")
            
            # Ingest file (it will copy to uploads persistently)
            logger.info(f"Uploading and ingesting: {safe_filename}")
            res = pipeline.ingest_file(temp_file_path, copy_to_uploads=True)
            results.append(res)
        except Exception as e:
            logger.error(f"Failed to ingest uploaded file {safe_filename}: {e}")
            results.append({"doc_id": safe_filename, "status": "error", "error": f"File parsing failed: {str(e)}"})
        finally:
            # Clean up temporary file
            if temp_file_path.exists():
                os.remove(temp_file_path)
                
    return {"results": results}


@app.post("/ingest/initialize")
async def initialize_corpus():
    """Clear database and ingest all files in default corpus directories."""
    try:
        pipeline = IngestionPipeline()
        stats = pipeline.initialize_corpus()
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Error during corpus initialization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize corpus: {str(e)}")


# --- Document Information Endpoints ---

@app.get("/documents")
async def list_documents():
    """List all ingested documents with metadata."""
    pipeline = IngestionPipeline()
    return pipeline.list_documents()


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get full details and chunks for a specific document."""
    store = get_vector_store()
    
    # Query ChromaDB for all chunks where doc_id matches
    # Use ChromaDB client collection.get
    try:
        results = store.collection.get(where={"doc_id": doc_id})
        
        if not results or not results["ids"]:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found or has no chunks.")
            
        chunks = []
        for i in range(len(results["ids"])):
            chunks.append({
                "chunk_id": results["ids"][i],
                "text": results["documents"][i],
                "metadata": results["metadatas"][i]
            })
            
        # Sort chunks by chunk_index to ensure text is in order
        chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))
        
        return {
            "doc_id": doc_id,
            "filename": doc_id,
            "chunk_count": len(chunks),
            "chunks": chunks
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Query Endpoint ───────────────────────────────────────────────────────────


def _build_trace(
    context: dict,
    routing_mode: str = "auto",
    latency_ms: int = 0,
    cache: str = "miss",
    model: str = "",
    thinking: Optional[bool] = None,
    complexity: Optional[bool] = None,
) -> dict:
    """Build the per-stage pipeline trace surfaced in the "Why this answer?" panel.

    Phase 5 (UI pass): the frontend renders a Query → Cache → Hybrid Retrieve →
    Rerank → Graph → LLM → Answer step indicator from this dict, so every field
    must reflect what actually happened in this request.
    """
    return {
        "cache": cache,
        "hybrid": bool(settings.use_hybrid),
        "reranker": bool(settings.use_reranker),
        "candidates": len(context.get("candidate_chunks", [])),
        "chunks_used": len(context.get("vector_chunks", [])),
        "graph_entities": len(context.get("graph_entities", [])),
        "graph_relations": len(context.get("graph_relations", [])),
        "complexity": complexity,
        "thinking": thinking,
        "model": model,
        "routing_mode": routing_mode,
        "latency_ms": latency_ms,
    }


@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """POST /query — retrieve context then generate a structured answer.

    Uses query_engine.retrieve_context() (vector + graph) then
    query_engine.generate_answer() (Ollama LLM or smart fallback).
    Returns {answer, sources, confidence, entities_used, key_points, model_used}.
    """
    t_start = time.time()

    # ── Guard: empty question ───────────────────────────────────────────────
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    try:
        logger.info(f"POST /query: '{request.question}'")

        # ── Guard: empty database ────────────────────────────────────────────
        store = get_vector_store()
        if store.count() == 0:
            return QueryResponse(
                answer=(
                    "No documents indexed yet. "
                    "Please open the **Control & Setup Panel** tab and click "
                    "**Scan & Index Default Corpus** to initialise the system."
                ),
                sources=[],
                confidence=0.0,
                entities_used=[],
                key_points=[],
                model_used="N/A",
                latency_ms=0,
            )

        # ── Step 1: Retrieve merged context (vector + graph) ────────────────────
        top_k   = request.top_k or settings.top_k
        context = retrieve_context(request.question, top_k=top_k, filters=request.filters)

        # ── Guard: no results found ────────────────────────────────────────────
        if not context["vector_chunks"] and not context["graph_entities"]:
            return QueryResponse(
                answer=(
                    "No matching documents or entities were found for your query. "
                    "Try rephrasing, or check that the corpus has been indexed."
                ),
                sources=[],
                confidence=0.0,
                entities_used=[],
                key_points=[],
                model_used="N/A",
                latency_ms=int((time.time() - t_start) * 1000),
            )

        # ── Step 2: Generate answer (LLM / smart fallback) ─────────────────────
        ans = generate_answer(request.question, context, routing_mode=request.routing_mode)

        latency_ms = int((time.time() - t_start) * 1000)
        logger.info(
            f"/query answered in {latency_ms} ms | "
            f"confidence={ans.get('confidence')} | model={ans.get('model_used')}"
        )

        # ── Phase 5: per-stage trace for the evidence panel ─────────────────────
        model_used = ans.get("model_used", "unknown")
        cache_status = "hit" if "Semantic Cache" in str(model_used) else "miss"
        complexity = None
        thinking = None
        if (request.routing_mode or "auto") == "auto":
            try:
                complexity = classify_query_complexity(request.question, context.get("vector_chunks", [])).get("is_complex")
                thinking = not complexity
            except Exception:
                pass

        return QueryResponse(
            answer       = ans.get("answer", ""),
            sources      = ans.get("sources", []),
            confidence   = ans.get("confidence", 0.0),
            entities_used= ans.get("entities_used", []),
            key_points   = ans.get("key_points", []),
            model_used   = model_used,
            latency_ms   = latency_ms,
            trace        = _build_trace(
                context, routing_mode=request.routing_mode or "auto",
                latency_ms=latency_ms, cache=cache_status,
                model=model_used, thinking=thinking, complexity=complexity,
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in POST /query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Streaming Query Endpoint (Tier 3.1 / 3.2) ──────────────────────────────

@app.post("/query/stream")
async def query_rag_stream(request: QueryRequest):
    """POST /query/stream — SSE streaming version of /query.

    Returns a Server-Sent Events stream. Each event is a JSON object:
      {"type": "token",   "content": "<token>"}
      {"type": "metadata", "content": {sources, confidence, entities_used, key_points, model_used, latency_ms}}
      {"type": "error",   "content": "<message>"}
      {"type": "done",    "content": ""}
    """
    t_start = time.time()

    if not request.question or not request.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    # ── Pre-flight: retrieve context (vector + graph) synchronously ───────────
    store = get_vector_store()
    if store.count() == 0:
        async def _empty_gen():
            yield f"data: {json.dumps({'type': 'metadata', 'content': {'answer': 'No documents indexed yet.', 'sources': [], 'confidence': 0.0, 'entities_used': [], 'key_points': [], 'model_used': 'N/A', 'latency_ms': 0}})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        return StreamingResponse(_empty_gen(), media_type="text/event-stream")

    # ── Semantic-cache fast-path (Phase 5 trace: Cache stage can actually HIT) ─
    # The non-stream /query path checks the cache inside generate_answer(); the
    # streaming endpoint used to only *write* to the cache. Check it up front so
    # duplicate queries stream the cached answer instantly instead of hitting
    # the LLM again.
    routing_mode = request.routing_mode or "auto"
    if routing_mode == "auto" and settings.use_semantic_cache:
        try:
            embedder = get_embedder()
            qe = np.array(embedder.embed_query(request.question))
            _cached_res = _semantic_cache.get(qe)
        except Exception as e:
            logger.error(f"Semantic cache read failed in /query/stream: {e}")
            _cached_res = None
    else:
        _cached_res = None

    if _cached_res is not None:
        cached = copy.deepcopy(_cached_res)
        cached.setdefault("latency_ms", 0)
        cached.setdefault("sources", [])
        cached.setdefault("entities_used", [])
        cached.setdefault("key_points", [])
        cached["model_used"] = f"{cached.get('model_used', '')} (Semantic Cache)"
        cached["trace"] = _build_trace(
            {}, routing_mode="auto", latency_ms=cached.get("latency_ms", 0),
            cache="hit", model=cached.get("model_used", "Semantic Cache"),
        )

        async def _cached_gen():
            yield f"data: {json.dumps({'type': 'token', 'content': cached.get('answer', '')})}\n\n"
            yield f"data: {json.dumps({'type': 'metadata', 'content': cached})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        return StreamingResponse(
            _cached_gen(), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    top_k = request.top_k or settings.top_k
    context = retrieve_context(request.question, top_k=top_k, filters=request.filters)

    if not context["vector_chunks"] and not context["graph_entities"]:
        async def _no_results_gen():
            yield f"data: {json.dumps({'type': 'metadata', 'content': {'answer': 'No matching documents found.', 'sources': [], 'confidence': 0.0, 'entities_used': [], 'key_points': [], 'model_used': 'N/A', 'latency_ms': 0}})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        return StreamingResponse(_no_results_gen(), media_type="text/event-stream")

    # ── Build the prompt (reuses shared helpers from query_engine) ────────────

    chunks   = context.get("vector_chunks", [])
    entities = context.get("graph_entities", [])
    relations = context.get("graph_relations", [])

    n_chunks    = len(chunks)
    n_entities  = len(entities)
    n_relations = len(relations)

    if n_chunks >= 2 and n_entities >= 1:
        guidance_conf = "High   (0.80-1.00)"
    elif n_chunks >= 1 or n_entities >= 1:
        guidance_conf = "Medium (0.50-0.79)"
    else:
        guidance_conf = "Low    (0.00-0.49)"

    doc_parts: List[str] = []
    source_list: List[dict] = []
    for i, c in enumerate(chunks, 1):
        doc_id  = c["metadata"].get("doc_id", c.get("chunk_id", "unknown"))
        text    = c["text"].strip()
        dist    = c.get("distance", 0.0)
        score   = round(1.0 - float(dist), 3)
        doc_parts.append(f"[Source {i}] {doc_id}  (relevance: {score})\n{text}")
        source_list.append({"doc_id": doc_id, "excerpt": text[:250], "distance": dist})

    doc_context = "\n\n---\n\n".join(doc_parts) or "No documents retrieved."

    graph_lines: List[str] = []
    for rel in relations[:10]:
        graph_lines.append(f"  {rel['source']} --[{rel['relation']}]--> {rel['target']}")
    if not graph_lines:
        graph_lines = ["  No knowledge-graph relationships found for this query."]
    graph_context = "\n".join(graph_lines)

    entity_ids = [e["id"] for e in entities]

    conf_guide = _CONFIDENCE_GUIDE.format(
        n_chunks=n_chunks, n_entities=n_entities, n_relations=n_relations,
    ) + f"  Suggested confidence band: {guidance_conf}"

    prompt = _RAG_TEMPLATE.format(
        doc_context=doc_context, graph_context=graph_context,
        question=request.question, confidence_guide=conf_guide,
    )

    # ── Determine Model and Reasoning Settings based on Routing Mode ──────────
    routing_mode = request.routing_mode or "auto"
    complexity = None
    if routing_mode == "fast":
        target_model = "meta/llama-3.1-8b-instruct"
        enable_thinking = False
        reasoning_budget = 0
        tokens_limit = 1024
        logger.info("Routing override: fast answer -> model=meta/llama-3.1-8b-instruct, enable_thinking=False")
    elif routing_mode == "deep":
        target_model = "nvidia/nemotron-3-ultra-550b-a55b"
        enable_thinking = True
        reasoning_budget = 1024
        tokens_limit = 2048
        logger.info("Routing override: deep reasoning -> model=nvidia/nemotron-3-ultra-550b-a55b, enable_thinking=True")
    else:  # "auto"
        complexity = classify_query_complexity(request.question, chunks)
        enable_thinking = complexity["enable_thinking"]
        reasoning_budget = complexity["reasoning_budget"]
        # Simple lookups -> fast 8B model. The 550B's ~40s+ first token blows
        # Render free tier's 60s request limit; deep synthesis stays on 550B.
        if enable_thinking:
            target_model = settings.nvidia_model
        else:
            target_model = "meta/llama-3.1-8b-instruct"
            logger.info("Auto routing (stream): simple query -> meta/llama-3.1-8b-instruct")
        tokens_limit = 2048 if enable_thinking else 1024

    llm = get_llm()
    is_nvidia = isinstance(llm, NvidiaLLM)
    llm_label = "NVIDIA API" if is_nvidia else ("Ollama" if isinstance(llm, OllamaLLM) else "Smart Context")

    # ── Phase 5: per-stage trace emitted with the metadata event ──────────────
    trace = _build_trace(
        context, routing_mode=routing_mode, cache="miss",
        model=target_model, thinking=enable_thinking,
        complexity=complexity["is_complex"] if complexity else None,
    )

    # ── Generator: stream tokens via SSE ──────────────────────────────────────
    async def event_stream():
        full_answer_parts: list = []
        error_msg: str = ""

        try:
            if llm.available and is_nvidia:
                for token in llm.stream_generate(
                    prompt, max_tokens=tokens_limit,
                    enable_thinking=enable_thinking,
                    reasoning_budget=reasoning_budget,
                    model=target_model,
                ):
                    full_answer_parts.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            elif llm.available:
                raw = llm.generate(prompt, max_tokens=settings.max_tokens)
                if raw:
                    full_answer_parts.append(raw)
                    yield f"data: {json.dumps({'type': 'token', 'content': raw})}\n\n"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
        finally:
            # Always send metadata + done, even on mid-stream errors
            full_text = "".join(full_answer_parts)
            try:
                result = _extract_json(full_text)
            except Exception:
                result = {"answer": full_text, "confidence": "Medium", "key_points": [], "entities_mentioned": []}

            latency_ms = int((time.time() - t_start) * 1000)
            result.setdefault("key_points", [])
            result.setdefault("entities_mentioned", [])
            result["entities_used"] = list(set(result.get("entities_mentioned", []) + entity_ids))
            result["sources"] = source_list
            result["model_used"] = f"{llm_label} / {target_model}" if is_nvidia else llm_label
            result["latency_ms"] = latency_ms
            result["confidence"] = result.get("confidence", "Medium")
            if error_msg:
                result["error"] = error_msg
            trace["latency_ms"] = latency_ms
            result["trace"] = trace

            if routing_mode == "auto":
                try:
                    embedder = get_embedder()
                    qe = np.array(embedder.embed_query(request.question))
                    _semantic_cache.set(qe, result)
                except Exception:
                    pass

            yield f"data: {json.dumps({'type': 'metadata', 'content': result})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})



# ── Benchmark Endpoint ────────────────────────────────────────────────────────

@app.get("/benchmark/run")
async def run_benchmark(max_questions: int = Query(default=18, le=50)):
    """Run the ground-truth Q&A benchmark and return accuracy metrics."""
    qa_file = settings.benchmarks_dir / "qa_pairs.json"
    if not qa_file.exists():
        raise HTTPException(status_code=404, detail="No benchmark file found at data/benchmarks/qa_pairs.json")

    try:
        qa_pairs = json.loads(qa_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load benchmark file: {e}")

    store    = get_vector_store()

    if store.count() == 0:
        raise HTTPException(status_code=400, detail="Vector store is empty. Run /ingest/initialize first.")

    results   = []
    total     = min(len(qa_pairs), max_questions)
    correct   = 0
    total_ms  = 0
    retrieval_log = []  # Track retrieval sources for each question

    for qa in qa_pairs[:total]:
        t0 = time.time()
        question = qa["question"]
        expected = qa["answer"].lower()

        context = retrieve_context(question, top_k=50)
        
        # Log retrieval sources for this question
        retrieved_chunks = context.get("vector_chunks", [])
        chunk_sources = []
        for chunk in retrieved_chunks:
            meta = chunk.get("metadata", {})
            chunk_sources.append({
                "doc_id": meta.get("doc_id", "unknown"),
                "chunk_index": meta.get("chunk_index", 0),
                "distance": round(chunk.get("distance", 0.0), 4),
                "record_type": meta.get("record_type", "unknown"),
                "excerpt": chunk.get("text", "")[:150]
            })
        
        llm_result = generate_answer(question, context)
        
        answer_text = llm_result.get("answer", "")
        sources_list = llm_result.get("sources", [])
        retrieved_source_docs = {s.get("citation", s.get("doc_id", "")) for s in sources_list}
        
        elapsed_ms = int((time.time() - t0) * 1000)
        total_ms += elapsed_ms

        expected_source_docs = set(qa.get("source_docs", []))

        # 1. Keyword overlap scoring (saved for comparison)
        expected_keywords = set(expected.split())
        answer_lower      = answer_text.lower()
        matches = sum(1 for kw in expected_keywords if len(kw) > 4 and kw in answer_lower)
        hit_text_keyword = matches >= max(1, len(expected_keywords) // 4)

        # 2. Embedding similarity scoring
        embedder = TextEmbedder()
        emb_expected = embedder.embed_query(qa["answer"])
        emb_got = embedder.embed_query(answer_text)
        val_dot = np.dot(emb_expected, emb_got)
        val_norm = (np.linalg.norm(emb_expected) * np.linalg.norm(emb_got))
        similarity = val_dot / val_norm if val_norm > 0 else 0.0
        hit_text_semantic = similarity >= settings.similarity_threshold

        # Primary text match criteria is semantic similarity
        hit_text = hit_text_semantic

        hit_source = True
        if expected_source_docs:
            hit_source = any(
                any(es.lower() in rs.lower() for rs in retrieved_source_docs)
                for es in expected_source_docs
            )

        hit = bool(hit_text and hit_source)
        if hit:
            correct += 1

        reason = []
        if not hit_text: reason.append(f"semantic similarity too low ({similarity:.3f} < {settings.similarity_threshold})")
        if expected_source_docs and not hit_source: reason.append("wrong source retrieved")
        if llm_result.get("confidence") == "Low": reason.append("low confidence")
        reason_str = ", ".join(reason) if not hit else ""

        # Store in retrieval log
        retrieval_log.append({
            "id": qa.get("id", ""),
            "question": question,
            "status": "PASS" if hit else "FAIL",
            "similarity": round(float(similarity), 4),
            "expected_source_docs": list(expected_source_docs),
            "retrieved_source_docs": list(retrieved_source_docs),
            "chunk_sources": chunk_sources,
            "llm_sources": sources_list[:3]
        })

        results.append({
            "id":           qa.get("id", ""),
            "question":     question,
            "expected":     qa["answer"],
            "got":          answer_text[:300],
            "confidence":   llm_result.get("confidence", "Low"),
            "passed":       hit,
            "reason":       reason_str,
            "latency_ms":   elapsed_ms,
            "category":     qa.get("category", ""),
            "similarity":   float(similarity),
            "passed_keyword": bool(hit_text_keyword),
        })
        logger.info(f"Benchmark {qa.get('id')}: {'PASS' if hit else 'FAIL'} ({elapsed_ms} ms) - {reason_str}")

    accuracy = round(correct / total * 100, 1) if total > 0 else 0.0
    avg_ms   = round(total_ms / total) if total > 0 else 0

    # Save retrieval log to disk for post-benchmark analysis
    retrieval_log_path = settings.benchmarks_dir / "retrieval_log.json"
    try:
        retrieval_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(retrieval_log_path, "w") as f:
            json.dump(retrieval_log, f, indent=2)
        logger.info(f"Retrieval log saved to: {retrieval_log_path}")
    except Exception as e:
        logger.warning(f"Failed to save retrieval log: {e}")

    return {
        "total":           total,
        "correct":         correct,
        "accuracy_pct":    accuracy,
        "avg_latency_ms":  avg_ms,
        "model_used":      get_llm().model or "smart-fallback",
        "results":         results,
        "retrieval_log":   retrieval_log,  # Include log for debugging regressions
    }


# ── Feedback Endpoint ─────────────────────────────────────────────────────────

@app.post("/feedback")
async def log_feedback(request: FeedbackRequest):
    """Log thumbs-up (+1) or thumbs-down (-1) feedback on an answer."""
    entry = {
        "ts":       time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "question": request.question,
        "answer":   request.answer[:300],
        "rating":   request.rating,
        "comment":  request.comment or "",
    }
    try:
        _FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(f"Feedback logged: rating={request.rating}")
    except Exception as e:
        logger.error(f"Failed to write feedback: {e}")
    return {"status": "logged"}


# ── Debug: raw vector search (no LLM) ────────────────────────────────────────

@app.get("/debug/search")
async def debug_search(
    q: str = Query(..., description="Raw search query — no LLM, pure vector similarity"),
    n: int = Query(default=5, le=20),
):
    """Raw vector similarity search without LLM — useful for tuning chunk size / top-k."""
    try:
        embedder = TextEmbedder()
        store    = get_vector_store()
        emb      = embedder.embed_query(q)
        results  = store.query(emb, n_results=n)

        hits = []
        if results and results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                hits.append({
                    "rank":     i + 1,
                    "doc_id":   results["metadatas"][0][i].get("doc_id", "?"),
                    "distance": round(results["distances"][0][i], 4),
                    "score":    round(1 - results["distances"][0][i], 4),
                    "excerpt":  results["documents"][0][i][:300],
                    "metadata": results["metadatas"][0][i],
                })
        return {"query": q, "hits": hits, "total_in_db": store.count()}
    except Exception as e:
        logger.error(f"Debug search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── LLM status endpoint ───────────────────────────────────────────────────────

@app.get("/llm/status")
async def llm_status():
    """Check whether NVIDIA NIM or Ollama is running and which model is selected."""
    llm = get_llm()
    is_nvidia = isinstance(llm, NvidiaLLM)
    is_ollama = isinstance(llm, OllamaLLM)
    return {
        "nvidia_available": is_nvidia and llm.available,
        "ollama_available": is_ollama and llm.available,
        "model":            llm.model or "none",
        "base_url":         llm.base_url,
        "mode":             "nvidia" if is_nvidia else ("ollama" if is_ollama else "smart-context-fallback"),
    }
