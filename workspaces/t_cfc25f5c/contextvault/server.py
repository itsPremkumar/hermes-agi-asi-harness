"""HTTP server for ContextVault — REST API for memory operations."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from contextvault.access_control import AccessController
from contextvault.consolidation import ConsolidationPipeline
from contextvault.memory_store import MemoryStore
from contextvault.models import (
    AccessLevel,
    MemoryMetadata,
    MemoryTier,
    MemoryType,
)
from contextvault.relevance import RelevanceScorer
from contextvault.search import MemorySearch
from contextvault.ttl import ColdStorage, TTLManager
from contextvault.vector_store import HashEmbeddingProvider, VectorStore

logger = logging.getLogger(__name__)


class StoreRequest(BaseModel):
    """Request to store a new memory."""
    content: str
    memory_type: str = "fact"
    tier: str = "semantic"
    agent_id: str = "default"
    tags: List[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    ttl: Optional[float] = None
    access_level: str = "private"


class SearchRequest(BaseModel):
    """Request to search memories."""
    query: str
    top_k: int = 10
    mode: str = "hybrid"
    tier: Optional[str] = None
    memory_type: Optional[str] = None
    agent_id: Optional[str] = None
    tags: Optional[List[str]] = None
    min_score: float = 0.0


class PromoteRequest(BaseModel):
    """Request to promote a memory."""
    memory_id: str
    target_tier: str


class RelateRequest(BaseModel):
    """Request to create a relationship."""
    source_id: str
    target_id: str
    relation_type: str = "related_to"
    strength: float = 0.5


class ShareRequest(BaseModel):
    """Request to share a memory."""
    memory_id: str
    target_agents: List[str]


class ConsolidateRequest(BaseModel):
    """Request to consolidate memories."""
    memory_ids: List[str]
    target_tier: str = "semantic"
    operation: str = "merge"


class RegisterAgentRequest(BaseModel):
    """Request to register an agent."""
    agent_id: str
    name: str
    description: str = ""


# Global state
_store: Optional[MemoryStore] = None
_access_controller: Optional[AccessController] = None
_search_engine: Optional[MemorySearch] = None
_ttl_manager: Optional[TTLManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize global state on startup."""
    global _store, _access_controller, _search_engine, _ttl_manager

    _store = MemoryStore(dimension=128)
    _access_controller = AccessController()
    _search_engine = MemorySearch(_store._vector_store, RelevanceScorer())
    _ttl_manager = TTLManager()

    logger.info("ContextVault HTTP server initialized")
    yield
    logger.info("ContextVault HTTP server shutting down")


app = FastAPI(
    title="ContextVault",
    description="Agent Long-Term Memory Store — REST API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/api/v1/memories")
async def store_memory(req: StoreRequest) -> Dict[str, Any]:
    """Store a new memory."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    try:
        memory_type = MemoryType(req.memory_type)
        tier = MemoryTier(req.tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    metadata = MemoryMetadata(
        agent_id=req.agent_id,
        importance=req.importance,
        confidence=req.confidence,
        tags=req.tags,
        access_level=AccessLevel(req.access_level),
    )

    memory = _store.store(
        content=req.content,
        memory_type=memory_type,
        tier=tier,
        metadata=metadata,
        ttl=req.ttl,
    )

    return {
        "id": memory.id,
        "content": memory.content,
        "tier": memory.tier.value,
        "type": memory.memory_type.value,
        "created_at": memory.created_at,
    }


@app.get("/api/v1/memories/{memory_id}")
async def get_memory(memory_id: str) -> Dict[str, Any]:
    """Get a memory by ID."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    memory = _store.recall(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory.to_document()


@app.post("/api/v1/search")
async def search_memories(req: SearchRequest) -> Dict[str, Any]:
    """Search memories using hybrid search."""
    if _store is None or _search_engine is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    # Index all memories for search
    all_memories = _store.list_memories()
    for mem in all_memories:
        _search_engine.index_memory(mem)

    tier = MemoryTier(req.tier) if req.tier else None
    memory_type = MemoryType(req.memory_type) if req.memory_type else None

    results = _search_engine.search(
        query=req.query,
        top_k=req.top_k,
        mode=req.mode,
        tier=tier,
        memory_type=memory_type,
        agent_id=req.agent_id,
        tags=req.tags,
        min_score=req.min_score,
    )

    return {
        "results": results,
        "total": len(results),
        "query": req.query,
    }


@app.get("/api/v1/search")
async def search_memories_get(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(10, ge=1, le=100),
    tier: Optional[str] = None,
    memory_type: Optional[str] = None,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Search memories using GET (convenience endpoint)."""
    req = SearchRequest(
        query=query,
        top_k=top_k,
        tier=tier,
        memory_type=memory_type,
        agent_id=agent_id,
    )
    return await search_memories(req)


@app.post("/api/v1/memories/{memory_id}/promote")
async def promote_memory(memory_id: str, req: PromoteRequest) -> Dict[str, Any]:
    """Promote a memory to a higher tier."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    try:
        target_tier = MemoryTier(req.target_tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    memory = _store.promote(memory_id, target_tier)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"id": memory.id, "tier": memory.tier.value}


@app.post("/api/v1/memories/{memory_id}/archive")
async def archive_memory(memory_id: str) -> Dict[str, Any]:
    """Archive a memory."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    if _store.archive(memory_id):
        return {"id": memory_id, "archived": True}
    raise HTTPException(status_code=404, detail="Memory not found")


@app.post("/api/v1/relations")
async def create_relation(req: RelateRequest) -> Dict[str, Any]:
    """Create a relationship between two memories."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    relation = _store.relate(req.source_id, req.target_id, req.relation_type, req.strength)
    if relation is None:
        raise HTTPException(status_code=404, detail="One or both memories not found")

    return {
        "id": relation.id,
        "source_id": relation.source_id,
        "target_id": relation.target_id,
        "type": relation.relation_type,
    }


@app.get("/api/v1/memories/{memory_id}/relations")
async def get_relations(memory_id: str) -> Dict[str, Any]:
    """Get all relations for a memory."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    relations = _store.get_relations(memory_id)
    return {
        "relations": [
            {
                "id": r.id,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "type": r.relation_type,
                "strength": r.strength,
            }
            for r in relations
        ]
    }


@app.post("/api/v1/agents/register")
async def register_agent(req: RegisterAgentRequest) -> Dict[str, Any]:
    """Register a new agent."""
    if _access_controller is None:
        raise HTTPException(status_code=503, detail="Access controller not initialized")

    profile = _access_controller.register_agent(
        req.agent_id, req.name, req.description
    )
    return {
        "agent_id": profile.agent_id,
        "name": profile.name,
        "description": profile.description,
    }


@app.post("/api/v1/memories/{memory_id}/share")
async def share_memory(memory_id: str, req: ShareRequest) -> Dict[str, Any]:
    """Share a memory with other agents."""
    if _store is None or _access_controller is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    memory = _store.recall(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    success = _access_controller.share_memory(memory, memory.metadata.agent_id, req.target_agents)
    if not success:
        raise HTTPException(status_code=403, detail="Cannot share this memory")

    return {"id": memory_id, "access_level": "shared", "shared_with": req.target_agents}


@app.post("/api/v1/consolidate")
async def consolidate_memories(req: ConsolidateRequest) -> Dict[str, Any]:
    """Consolidate memories."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    pipeline = ConsolidationPipeline()
    memories = []
    for mid in req.memory_ids:
        mem = _store.recall(mid)
        if mem is None:
            raise HTTPException(status_code=404, detail=f"Memory {mid} not found")
        memories.append(mem)

    try:
        target_tier = MemoryTier(req.target_tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = pipeline.consolidate(memories, target_tier, req.operation)
    if result is None:
        raise HTTPException(status_code=400, detail="Consolidation failed")

    return {
        "id": result.id,
        "content": result.content,
        "tier": result.tier.value,
        "operation": req.operation,
    }


@app.get("/api/v1/stats")
async def get_stats() -> Dict[str, Any]:
    """Get store statistics."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not initialized")

    return _store.get_stats()


@app.get("/api/v1/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0", "timestamp": time.time()}


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the HTTP server."""
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
