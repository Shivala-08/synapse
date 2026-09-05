"""Synapse — Graph-Augmented RAG Intelligence Engine.

FastAPI application providing RAG query, ingestion, knowledge graph,
and document management endpoints.
"""

import copy
import json
import os
import shutil
import time
from datetime import date, datetime, timedelta
from contextlib import asynccontextmanager

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi import File, UploadFile, HTTPException, Query, Response, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from src.database.connection import get_db
from src.database.models import FeedbackLog
from pydantic import BaseModel, Field
from loguru import logger
import networkx as nx

from src.config import settings, get_active_domain_profile, load_domain_profile, list_domains
from src.pipeline.ingest import IngestionPipeline, doc_id_for_path
from src.pipeline.embedder import TextEmbedder
from src.pipeline.extractor import extract_entities
from src.pipeline.compliance import check_compliance
from src.pipeline.llm import get_llm, NvidiaLLM, OllamaLLM, _extract_json
from src.pipeline.query_engine import (
    retrieve_context, generate_answer, get_embedder,
    build_rag_prompt, _semantic_cache,
    classify_query_complexity, get_vector_store,
    init_bm25_index_lazy,
)
from src.storage.chroma_store import VectorStore
from src.graph.knowledge_graph import get_knowledge_graph
from src.database.connection import init_db
import numpy as np

# In-memory feedback store (persisted to disk on each write)
_FEEDBACK_FILE = settings.data_dir / "feedback.jsonl"


def _log_telemetry(
    db: Session,
    query_text: str,
    retrieval_ms: int = 0,
    generation_ms: int = 0,
    total_latency_ms: int = 0,
    model_used: str = "unknown",
    cache_hit: str = "false",
    error_occurred: str = "false",
) -> None:
    """Write a telemetry row to the database. Errors are logged but never raised."""
    try:
        from src.database.models import TelemetryLog
        db_log = TelemetryLog(
            query_text=query_text,
            retrieval_ms=retrieval_ms,
            llm_generation_ms=generation_ms,
            total_latency_ms=total_latency_ms,
            model_used=model_used,
            cache_hit=cache_hit,
            error_occurred=error_occurred,
        )
        db.add(db_log)
        db.commit()
    except Exception as e:
        logger.warning(f"Telemetry logging failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG-powered industrial knowledge system with vector search + knowledge graph.",
)

# Serve static assets (e.g. bundled JS libraries)
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.isdir(_static_dir):
    static_app = StaticFiles(directory=str(_static_dir))
    static_app = CORSMiddleware(static_app, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.mount("/static", static_app, name="static")

# CORS: comma-separated allow-list via CORS_ORIGINS. Unset → allow all origins
# WITHOUT credentials (Starlette's `*` + allow_credentials=True would echo any
# origin and effectively enable credentialed cross-site access).
_cors_list = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_list if _cors_list else ["*"],
    allow_credentials=bool(_cors_list),
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Pre-warming models and services...")
    try:
        init_db()
        get_embedder()
        get_vector_store()
        get_knowledge_graph()
        get_llm()

        # Pre-build BM25 indexes for all domains at startup so the first
        # query doesn't pay the lazy-init cost.
        try:
            for domain_id in list_domains():
                dp = load_domain_profile(domain_id)
                init_bm25_index_lazy(domain_profile=dp)
            logger.info("BM25 indexes pre-built for all domains.")
        except Exception as e:
            logger.warning(f"BM25 pre-build skipped: {e}")

        logger.info("Pre-warming complete. All services ready.")
    except Exception as e:
        logger.error(f"Error during startup pre-warming: {e}")
    if not settings.admin_api_key:
        if settings.require_admin_key:
            logger.critical(
                "ADMIN_API_KEY is NOT set but require_admin_key=True. "
                "Refusing to start in production mode without authentication. "
                "Set ADMIN_API_KEY in your .env file."
            )
            raise RuntimeError(
                "ADMIN_API_KEY is required when require_admin_key=True. "
                "Set it in your .env file before starting the server."
            )
        logger.warning(
            "ADMIN_API_KEY is NOT set — destructive endpoints (/ingest/*, "
            "/benchmark/run, /debug/search) are OPEN to anyone who can reach "
            "this server. Set ADMIN_API_KEY before exposing this publicly!"
        )
    yield


app.router.lifespan_context = lifespan


# ── Admin auth guard ──────────────────────────────────────────────────────
# When ADMIN_API_KEY is configured, protected endpoints require header
# X-API-Key: <key>. Unconfigured → open (local dev), with a startup warning.
async def require_admin(request: Request) -> None:
    if not settings.admin_api_key:
        return
    key = request.headers.get("x-api-key", "")
    if key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Forbidden: missing or invalid X-API-Key header.")


class ComplianceRequest(BaseModel):
    """Schema for compliance check requests."""
    requirement: str
    top_k: Optional[int] = 10


class QueryRequest(BaseModel):
    """Schema for incoming RAG queries."""
    question: str = Field(..., min_length=1, max_length=1000, description="The query string")
    # NOTE: default must satisfy the le=20 constraint — Pydantic v2 does NOT
    # validate defaults, so an out-of-range default sails through silently.
    top_k: Optional[int] = Field(default=10, ge=1, le=20)
    filters: Optional[dict] = None
    routing_mode: Optional[str] = Field("auto", description="Routing mode: 'auto', 'fast', or 'deep'")
    domain_id: Optional[str] = Field(None, description="Domain ID for multi-domain retrieval (e.g. 'second_brain', 'exam_prep')")


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
    domain: Optional[str] = None    # resolved domain ID for the query


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


@app.get("/domains")
async def list_available_domains():
    """List available domain profiles."""
    domains = list_domains()
    profiles = []
    for d in domains:
        try:
            p = load_domain_profile(d)
            profiles.append({
                "domain_id": p.domain_id,
                "display_name": p.display_name,
                "source_path": p.source_path,
                "collection_name": p.collection_name,
                "link_syntax": p.link_syntax,
            })
        except Exception as e:
            profiles.append({"domain_id": d, "error": str(e)})
    return {"domains": profiles}





@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.post("/compliance/check")
def compliance_check(request: ComplianceRequest):
    """Check a regulatory requirement against ingested procedures for gaps."""
    try:
        logger.info(f"Compliance check request: {request.requirement[:100]}...")
        result = check_compliance(request.requirement, top_k=request.top_k)
        return result
    except Exception as e:
        logger.error(f"Error during compliance check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph")
async def get_graph(
    max_nodes: int = Query(default=500, le=2000),
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the graph"),
):
    """Get the full knowledge graph as nodes/edges JSON for visualization.

    Falls back to the global graph when the domain graph is empty.
    """
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        # Fall back to global graph when domain graph is empty
        if kg.graph.number_of_nodes() == 0 and dp is not None:
            kg = get_knowledge_graph()
        return kg.to_json(max_nodes=max_nodes)
    except Exception as e:
        logger.error(f"Error fetching knowledge graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/search")
async def graph_search(
    q: str = Query(..., description="Search term to match against node IDs"),
    node_types: Optional[str] = Query(default=None, description="Comma-separated list of node types to filter by"),
    limit: int = Query(default=50, le=200, description="Max results to return"),
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the graph"),
):
    """Search for graph nodes by name/label."""
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        if kg.graph.number_of_nodes() == 0 and dp is not None:
            kg = get_knowledge_graph()
        types_list = [t.strip() for t in node_types.split(",")] if node_types else None
        matches = kg.search_nodes(q, node_types=types_list, limit=limit)
        return {"query": q, "results": matches, "count": len(matches)}
    except Exception as e:
        logger.error(f"Error searching graph nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/node/{node_id}")
async def get_graph_node(
    node_id: str,
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the graph"),
):
    """Get node metadata, immediate neighbors, and linked resource IDs."""
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        return kg.get_node_metadata(node_id)
    except Exception as e:
        logger.error(f"Error fetching node metadata for {node_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/top")
async def get_graph_top(
    n: int = Query(default=30, le=200, description="Number of top nodes to return"),
    node_types: Optional[str] = Query(default=None, description="Comma-separated list of node types to filter by"),
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the graph"),
):
    """Get top N most-connected nodes for initial graph loading."""
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        # Fall back to global graph when domain graph is empty
        if kg.graph.number_of_nodes() == 0 and dp is not None:
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
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the graph"),
):
    """Find shortest path between two entities in the knowledge graph."""
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        if kg.graph.number_of_nodes() == 0 and dp is not None:
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
async def graph_stats(
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the graph"),
):
    """Get detailed graph statistics for the dashboard."""
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        if kg.graph.number_of_nodes() == 0 and dp is not None:
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
def _fetch_subgraph_cached(entity_id: str, depth: int, domain_id: str = None) -> Optional[dict]:
    """Helper to fetch and format the subgraph, cached in-memory."""
    dp = load_domain_profile(domain_id) if domain_id else None
    kg = get_knowledge_graph(dp)
    if kg.graph.number_of_nodes() == 0 and dp is not None:
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
async def get_entity_subgraph(
    entity_id: str,
    depth: int = Query(default=1, le=2),
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the graph"),
):
    """Get subgraph centered on one entity for frontend visualization."""
    try:
        cached = _fetch_subgraph_cached(entity_id, depth, domain_id=domain_id)
        if not cached:
            raise HTTPException(
                status_code=404, 
                detail=f"Entity '{entity_id}' not found in the knowledge graph. Check the ID."
            )
        # Return a deep copy so callers cannot mutate the cached dict
        return copy.deepcopy(cached)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching entity subgraph for {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/entities")
async def get_entities(
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the graph"),
):
    """List all extracted entities grouped by type."""
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        if kg.graph.number_of_nodes() == 0 and dp is not None:
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


def _mastery_subjects(kg):
    """Per-entity-type graph coverage as a mastery estimate.

    For each entity type, mastery is the share of that type's entities that
    are linked into the knowledge graph (degree > 0). The overall score is
    the entity-count-weighted average across types.
    """
    by_type = kg.get_entities_by_type()
    subjects = []
    total_entities = 0
    weighted = 0.0
    for etype in sorted(by_type):
        ids = by_type[etype]
        if not ids or etype == "unknown":
            continue
        connected = sum(1 for n in ids if kg.graph.degree(n) > 0)
        pct = round(connected / len(ids) * 100)
        subjects.append({
            "name": etype,
            "mastery_pct": pct,
            "total": len(ids),
            "connected": connected,
            "entity_ids": ids[:200],
        })
        total_entities += len(ids)
        weighted += pct * len(ids)
    overall = round(weighted / total_entities) if total_entities else 0
    return subjects, overall


@app.get("/mastery")
async def get_mastery(
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope mastery"),
):
    """Mastery estimate per entity type, derived from knowledge graph coverage."""
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        # No global fallback: an empty domain graph is a real signal (nothing
        # tracked yet for this domain), not a reason to show another domain's data.
        subjects, overall = _mastery_subjects(kg)
        return {
            "domain_id": dp.domain_id if dp else "__global__",
            "overall_pct": overall,
            "subjects": subjects,
            "basis": "graph coverage",
            "note": "Mastery is estimated from how many of each topic's entities are linked into the knowledge graph. It improves as sources are ingested and connected.",
        }
    except Exception as e:
        logger.error(f"Error computing mastery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/roadmap/plan")
async def get_roadmap_plan(
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the plan"),
    exam_date: Optional[str] = Query(default=None, description="Exam date in YYYY-MM-DD"),
    daily_hours: float = Query(default=2.0, ge=0.5, le=12.0),
):
    """Allocate study hours per day from today to the exam date.

    Weakest topics (lowest graph coverage) receive the largest share of each
    day's hours, proportional to their inverse mastery.
    """
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        kg = get_knowledge_graph(dp)
        # No global fallback for domain-scoped plans (see /mastery).
        subjects, _ = _mastery_subjects(kg)
        if not subjects:
            return {
                "days": [],
                "subjects": [],
                "days_remaining": 0,
                "shown_days": 0,
                "daily_hours": daily_hours,
                "note": "No topics to plan yet. Ingest sources for this domain first.",
            }
        weights = {s["name"]: max(0.1, (100 - s["mastery_pct"]) / 100) for s in subjects}
        wsum = sum(weights.values())
        max_w = max(weights.values())
        today = date.today()
        exam = None
        if exam_date:
            try:
                exam = date.fromisoformat(exam_date)
            except ValueError:
                exam = None
        days_remaining = (exam - today).days if exam else 90
        days_remaining = max(1, min(days_remaining, 365))
        shown = min(days_remaining, 120)
        days = []
        for i in range(shown):
            d = today + timedelta(days=i)
            blocks = []
            for s in subjects:
                h = round(daily_hours * weights[s["name"]] / wsum, 1)
                if h < 0.05:
                    continue
                blocks.append({
                    "subject": s["name"],
                    "hours": h,
                    "priority": round(10 * weights[s["name"]] / max_w),
                    "mastery_pct": s["mastery_pct"],
                })
            blocks.sort(key=lambda b: -b["hours"])
            days.append({
                "date": d.isoformat(),
                "weekday": d.strftime("%a"),
                "day": d.day,
                "month": d.strftime("%b"),
                "blocks": blocks,
            })
        return {
            "domain_id": dp.domain_id if dp else "__global__",
            "exam_date": exam.isoformat() if exam else None,
            "days_remaining": days_remaining,
            "shown_days": shown,
            "daily_hours": daily_hours,
            "subjects": subjects,
            "days": days,
            "basis": "inverse-mastery allocation",
        }
    except Exception as e:
        logger.error(f"Error building roadmap plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/re-sync")
def resync_domain(
    domain_id: str = Query(..., description="Domain ID whose source path should be re-scanned"),
    _: None = Depends(require_admin),
):
    """Scan a domain's source path and ingest files missing from its registry.

    This is the vault sync for domains like second_brain whose sources live
    outside the uploads directory (e.g. an Obsidian vault).
    """
    try:
        dp = load_domain_profile(domain_id)
        if not dp or not dp.source_path or not Path(dp.source_path).exists():
            raise HTTPException(status_code=400, detail=f"Domain '{domain_id}' has no readable source path.")
        pipeline = IngestionPipeline(domain_profile=dp)
        existing = {d.get("doc_id") for d in pipeline.list_documents()}
        src = Path(dp.source_path)
        allowed = {".txt", ".csv", ".pdf", ".docx", ".md", ".pptx"}
        added = []
        skipped = 0
        errors = []
        for item in sorted(src.rglob("*")):
            if not item.is_file() or item.name.startswith("."):
                continue
            if item.suffix.lower() not in allowed:
                continue
            if doc_id_for_path(item, src) in existing:
                skipped += 1
                continue
            try:
                res = pipeline.ingest_file(item, copy_to_uploads=False)
                if res.get("status") == "success":
                    added.append(item.name)
                else:
                    errors.append({"file": item.name, "error": res.get("error", "unknown")})
            except Exception as e:
                errors.append({"file": item.name, "error": str(e)})
        return {
            "domain_id": domain_id,
            "source_path": str(src),
            "added": added,
            "skipped_count": skipped,
            "errors": errors,
            "synced_at": datetime.now().isoformat(timespec="seconds"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-syncing domain {domain_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


SUPPORTED_EXTENSIONS = {".txt", ".csv", ".pdf", ".docx", ".md"}

def background_ingest_file(file_path: Path, domain_id: Optional[str] = None):
    try:
        dp = load_domain_profile(domain_id) if domain_id else None
        pipeline = IngestionPipeline(domain_profile=dp)
        logger.info(f"Background task starting: Ingesting file {file_path.name} (domain={domain_id or 'default'})")
        pipeline.ingest_file(file_path, copy_to_uploads=False)
        logger.info(f"Background task complete: Successfully ingested {file_path.name}")
    except Exception as e:
        logger.error(f"Background ingestion task failed for {file_path.name}: {e}")

@app.post("/ingest/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    domain_id: Optional[str] = Query(default=None, description="Domain ID to scope ingestion"),
    _: None = Depends(require_admin),
):
    """Upload and ingest one or more documents (PDF, DOCX, CSV, TXT) in the background."""
    dp = load_domain_profile(domain_id) if domain_id else None
    uploads_dir = settings.corpus_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        pipeline = IngestionPipeline(domain_profile=dp)
        existing_docs = pipeline.store.collection.get(include=["metadatas"])
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

        target_file_path = uploads_dir / safe_filename
        max_bytes = settings.max_upload_mb * 1024 * 1024
        try:
            # Save file directly to persistent uploads directory (size-capped)
            with open(target_file_path, "wb") as buffer:
                remaining = max_bytes
                while chunk := file.file.read(1024 * 1024):
                    remaining -= len(chunk)
                    if remaining < 0:
                        raise ValueError(f"File exceeds {settings.max_upload_mb} MB limit.")
                    buffer.write(chunk)
                
            if target_file_path.stat().st_size == 0:
                raise ValueError("File is empty or corrupted.")
            
            # Queue ingestion in background task (FastAPI native thread pool)
            logger.info(f"Queuing background ingestion for: {safe_filename} (domain={domain_id or 'default'})")
            background_tasks.add_task(background_ingest_file, target_file_path, domain_id)
            
            results.append({
                "doc_id": safe_filename,
                "status": "queued",
                "message": "Document queued for background parsing, embedding, and indexing."
            })
        except Exception as e:
            logger.error(f"Failed to copy uploaded file {safe_filename}: {e}")
            if target_file_path.exists():
                os.remove(target_file_path)
            results.append({"doc_id": safe_filename, "status": "error", "error": f"Upload failed: {str(e)}"})
                 
    return {"results": results}


@app.post("/ingest/initialize")
def initialize_corpus(_: None = Depends(require_admin)):
    """Clear database and ingest all files in default corpus directories."""
    try:
        pipeline = IngestionPipeline()
        stats = pipeline.initialize_corpus()
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Error during corpus initialization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize corpus: {str(e)}")


@app.get("/documents")
async def list_documents(domain_id: Optional[str] = Query(default=None, description="Domain ID to scope the list")):
    """List all ingested documents with metadata for a domain."""
    dp = load_domain_profile(domain_id) if domain_id else None
    pipeline = IngestionPipeline(domain_profile=dp)
    return pipeline.list_documents()


@app.get("/documents/{doc_id}")
def get_document(doc_id: str):
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
def query_rag(request: QueryRequest, db: Session = Depends(get_db)):
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

        # ── Resolve domain profile ────────────────────────────────────────────
        domain_profile = None
        if request.domain_id:
            try:
                domain_profile = load_domain_profile(request.domain_id)
            except FileNotFoundError:
                available = list_domains()
                raise HTTPException(
                    status_code=400,
                    detail=f"Domain '{request.domain_id}' not found. Available: {available}"
                )
        else:
            # Default to first available domain
            domain_profile = get_active_domain_profile()

        # ── Guard: empty database for this domain ──────────────────────────────
        store = get_vector_store(domain_profile=domain_profile)
        if store.count() == 0:
            return QueryResponse(
                answer=(
                    f"No documents indexed yet for the '{domain_profile.display_name}' domain. "
                    "Please ingest documents into this domain first."
                ),
                sources=[],
                confidence=0.0,
                entities_used=[],
                key_points=[],
                model_used="N/A",
                latency_ms=0,
                domain=domain_profile.domain_id,
            )

        # ── Step 1: Retrieve merged context (vector + graph) with timing ────────
        t_ret_start = time.time()
        top_k   = request.top_k or settings.top_k
        context = retrieve_context(request.question, top_k=top_k, filters=request.filters, domain_profile=domain_profile)
        retrieval_ms = int((time.time() - t_ret_start) * 1000)

        # ── Guard: no results found ────────────────────────────────────────────
        if not context["vector_chunks"] and not context["graph_entities"]:
            latency_ms = int((time.time() - t_start) * 1000)
            _log_telemetry(db, request.question, retrieval_ms=retrieval_ms,
                           total_latency_ms=latency_ms, model_used="N/A")
            return QueryResponse(
                answer=(
                    "No matching documents or entities were found for your query. "
                    "Try rephrasing, or check that the corpus has been indexed."
                ),
                sources=[],
                domain=domain_profile.domain_id,
                confidence=0.0,
                entities_used=[],
                key_points=[],
                model_used="N/A",
                latency_ms=latency_ms,
            )

        # ── Step 2: Generate answer (LLM / smart fallback) with timing ──────────
        t_gen_start = time.time()
        ans = generate_answer(request.question, context, routing_mode=request.routing_mode)
        generation_ms = int((time.time() - t_gen_start) * 1000)

        latency_ms = int((time.time() - t_start) * 1000)
        logger.info(
            f"/query answered in {latency_ms} ms (retrieval: {retrieval_ms}ms, generation: {generation_ms}ms) | "
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

        # Write to TelemetryLog (V2 Observability)
        _log_telemetry(
            db, request.question,
            retrieval_ms=retrieval_ms, generation_ms=generation_ms,
            total_latency_ms=latency_ms, model_used=model_used,
            cache_hit="true" if cache_status == "hit" else "false",
        )

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
            domain       = domain_profile.domain_id,
        )
    except HTTPException as http_err:
        _log_telemetry(db, request.question,
                       total_latency_ms=int((time.time() - t_start) * 1000),
                       error_occurred="true")
        raise http_err
    except Exception as e:
        _log_telemetry(db, request.question,
                       total_latency_ms=int((time.time() - t_start) * 1000),
                       error_occurred="true")
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

    # ── Resolve domain profile ────────────────────────────────────────────
    domain_profile = None
    if request.domain_id:
        try:
            domain_profile = load_domain_profile(request.domain_id)
        except FileNotFoundError:
            available = list_domains()
            raise HTTPException(
                status_code=400,
                detail=f"Domain '{request.domain_id}' not found. Available: {available}"
            )
    else:
        domain_profile = get_active_domain_profile()

    # ── Pre-flight: retrieve context (vector + graph) synchronously ───────────
    store = get_vector_store(domain_profile=domain_profile)
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
            # embed_query does an HTTP round-trip — keep it off the event loop
            def _cache_lookup():
                emb = np.array(get_embedder().embed_query(request.question))
                return emb, _semantic_cache.get(emb)
            qe, _cached_res = await run_in_threadpool(_cache_lookup)
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
    # Retrieval = embedding HTTP call + cross-encoder inference + BM25 + spaCy.
    # All synchronous CPU/IO work — must not block the event loop.
    context = await run_in_threadpool(
        retrieve_context, request.question, top_k=top_k, filters=request.filters, domain_profile=domain_profile
    )

    if not context["vector_chunks"] and not context["graph_entities"]:
        async def _no_results_gen():
            yield f"data: {json.dumps({'type': 'metadata', 'content': {'answer': 'No matching documents found.', 'sources': [], 'confidence': 0.0, 'entities_used': [], 'key_points': [], 'model_used': 'N/A', 'latency_ms': 0}})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
        return StreamingResponse(_no_results_gen(), media_type="text/event-stream")

    # ── Build the prompt (shared helper — single source of truth) ──────────

    chunks   = context.get("vector_chunks", [])
    entities = context.get("graph_entities", [])
    relations = context.get("graph_relations", [])
    entity_ids = [e["id"] for e in entities]

    prompt, source_list = build_rag_prompt(request.question, chunks, entities, relations)

    # ── Determine Model and Reasoning Settings based on Routing Mode ──────────
    routing_mode = request.routing_mode or "auto"
    complexity = None
    if routing_mode == "fast":
        target_model = "meta/llama-3.2-11b-vision-instruct"
        enable_thinking = False
        reasoning_budget = 0
        tokens_limit = 1024
        logger.info("Routing override: fast answer -> model=meta/llama-3.2-11b-vision-instruct, enable_thinking=False")
    elif routing_mode == "deep":
        target_model = "nvidia/nemotron-3-ultra-550b-a55b"
        enable_thinking = True
        reasoning_budget = 1024
        tokens_limit = 2048
        logger.info("Routing override: deep reasoning -> model=nvidia/nemotron-3-ultra-550b-a55b, enable_thinking=True")
    else:  # "auto"
        complexity = await run_in_threadpool(classify_query_complexity, request.question, chunks)
        enable_thinking = complexity["enable_thinking"]
        reasoning_budget = complexity["reasoning_budget"]
        # Simple lookups -> fast 8B model. The 550B's ~40s+ first token blows
        # Render free tier's 60s request limit; deep synthesis stays on 550B.
        if enable_thinking:
            target_model = settings.nvidia_model
        else:
            target_model = "meta/llama-3.2-11b-vision-instruct"
            logger.info("Auto routing (stream): simple query -> meta/llama-3.2-11b-vision-instruct")
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
                # stream_generate is a SYNC generator over a blocking SDK call.
                # Iterating it inline would stall the entire event loop between
                # tokens; pull each token via the threadpool instead.
                token_iter = llm.stream_generate(
                    prompt, max_tokens=tokens_limit,
                    enable_thinking=enable_thinking,
                    reasoning_budget=reasoning_budget,
                    model=target_model,
                )
                while True:
                    token = await run_in_threadpool(next, token_iter, None)
                    if token is None:
                        break
                    full_answer_parts.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            elif llm.available:
                raw = await run_in_threadpool(llm.generate, prompt, settings.max_tokens)
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
                    qe = np.array(await run_in_threadpool(embedder.embed_query, request.question))
                    await run_in_threadpool(_semantic_cache.set, qe, result)
                except Exception:
                    pass

            yield f"data: {json.dumps({'type': 'metadata', 'content': result})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})



# ── Benchmark Endpoint ────────────────────────────────────────────────────────

@app.get("/benchmark/run")
def run_benchmark(
    domain: Optional[str] = Query(default=None, description="Domain ID (e.g. second_brain, exam_prep). Falls back to first available domain."),
    max_questions: int = Query(default=18, le=50),
    _: None = Depends(require_admin),
):
    """Run the ground-truth Q&A benchmark and return accuracy metrics.

    Supports per-domain QA pairs: data/benchmarks/qa_pairs_{domain}.json
    Falls back to legacy data/benchmarks/qa_pairs.json if no domain specified.
    """
    # Resolve domain profile
    from src.config import get_active_domain_profile, load_domain_profile
    available_domains = list_domains()

    if domain:
        if domain not in available_domains:
            raise HTTPException(status_code=400, detail=f"Unknown domain '{domain}'. Available: {available_domains}")
        profile = load_domain_profile(domain)
        qa_file = settings.benchmarks_dir / f"qa_pairs_{domain}.json"
    else:
        # Backward compatible: try legacy qa_pairs.json, then first domain
        legacy_file = settings.benchmarks_dir / "qa_pairs.json"
        if legacy_file.exists():
            qa_file = legacy_file
            profile = None
        elif available_domains:
            profile = get_active_domain_profile()
            domain = profile.domain_id
            qa_file = settings.benchmarks_dir / f"qa_pairs_{domain}.json"
        else:
            raise HTTPException(status_code=400, detail="No domains configured and no legacy qa_pairs.json found.")

    if not qa_file.exists():
        raise HTTPException(status_code=404, detail=f"No benchmark file found at {qa_file}")

    try:
        qa_pairs = json.loads(qa_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load benchmark file: {e}")

    store = get_vector_store(domain_profile=profile)

    if store.count() == 0:
        raise HTTPException(status_code=400, detail=f"Vector store is empty for domain '{domain}'. Run /ingest/initialize first.")

    results   = []
    total     = min(len(qa_pairs), max_questions)
    correct   = 0
    total_ms  = 0
    retrieval_log = []  # Track retrieval sources for each question

    for qa in qa_pairs[:total]:
        t0 = time.time()
        question = qa["question"]
        expected = qa["answer"].lower()

        context = retrieve_context(question, top_k=50, domain_profile=profile)
        
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
async def log_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Log thumbs-up (+1) or thumbs-down (-1) feedback on an answer."""
    # Write to database (V2 transaction safety)
    try:
        log_entry = FeedbackLog(
            question=request.question,
            answer=request.answer[:300],
            rating=request.rating,
            comment=request.comment or ""
        )
        db.add(log_entry)
        db.commit()
        logger.info(f"Feedback logged to DB: rating={request.rating}")
    except Exception as e:
        logger.error(f"Failed to write feedback to DB: {e}")
        db.rollback()

    # Legacy JSONL fallback
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
        logger.info(f"Feedback logged to legacy file: rating={request.rating}")
    except Exception as e:
        logger.error(f"Failed to write legacy feedback file: {e}")
    return {"status": "logged"}


# ── Debug: raw vector search (no LLM) ────────────────────────────────────────

@app.get("/debug/search")
def debug_search(
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
