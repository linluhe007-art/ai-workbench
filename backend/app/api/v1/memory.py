"""
Memory API
Provides knowledge base queries, search, index, stats, and long-term memory management.
Phase 5.3: Long-term personal memory (PROFILE, PREFERENCE, PROJECT, KNOWLEDGE, EXPERIENCE).
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.memory.service import MemoryService
from app.memory.manager import MemoryManager, MemoryType, get_memory_manager, reset_memory_manager
from app.memory.retrieval import MemoryRetriever
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])

_memory: MemoryService | None = None
_ltm: MemoryManager | None = None


def _get_memory() -> MemoryService:
    global _memory
    if _memory is None:
        _memory = MemoryService()
    return _memory


def _get_ltm() -> MemoryManager:
    global _ltm
    if _ltm is None:
        _ltm = get_memory_manager()
    return _ltm


class SearchRequest(BaseModel):
    keyword: str
    limit: int = 10


# ── Existing knowledge base endpoints ───────────────────────────────────────

@router.get("/stats")
async def get_stats():
    """Get knowledge base stats."""
    mem = _get_memory()
    try:
        stats = mem.get_stats()
        return {"status": "ok", "data": stats}
    except Exception as e:
        logger.error("Memory stats failed", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/search")
async def search(req: SearchRequest):
    """Keyword search in knowledge base."""
    mem = _get_memory()
    results = mem.search(req.keyword, limit=req.limit)
    return {"keyword": req.keyword, "total": len(results), "results": results}


@router.get("/context")
async def get_context(q: str = Query(..., description="Query topic"), max_chars: int = 3000):
    """Get structured memory context."""
    mem = _get_memory()
    ctx = mem.get_memory_context(q, max_chars=max_chars)
    return {
        "query": q,
        "documents": ctx.documents,
        "tags": ctx.tags,
        "related_links": ctx.related_links,
        "summary": ctx.summary,
        "prompt_text": ctx.to_prompt(),
    }


@router.post("/refresh")
async def refresh(full: bool = False):
    """Refresh knowledge base index."""
    mem = _get_memory()
    count = mem.refresh() if full else mem.incremental_refresh()
    return {"status": "ok", "files_updated": count, "mode": "full" if full else "incremental"}


# ── Phase 5.3 Long-term Memory endpoints ─────────────────────────────────────

class SaveMemoryRequest(BaseModel):
    content: str
    memory_type: str = "knowledge"
    importance: float = 0.5
    tags: list[str] = []
    metadata: dict = {}
    embedding_id: str = ""


class UpdateMemoryRequest(BaseModel):
    content: str | None = None
    importance: float | None = None
    tags: list[str] | None = None
    metadata: dict | None = None


class LtmSearchRequest(BaseModel):
    query: str = ""
    memory_type: str | None = None
    tags: list[str] | None = None
    limit: int = 20
    min_importance: float = 0.0


@router.post("/ltm")
async def save_memory(req: SaveMemoryRequest):
    """Save a long-term memory record."""
    ltm = _get_ltm()
    try:
        record = ltm.save_memory(
            content=req.content,
            memory_type=req.memory_type,
            importance=req.importance,
            tags=req.tags,
            metadata=req.metadata,
            embedding_id=req.embedding_id,
        )
        return {"success": True, "data": record.to_dict()}
    except ValueError as e:
        return {"success": False, "error": str(e)}


@router.post("/ltm/search")
async def search_ltm(req: LtmSearchRequest):
    """Search long-term memories."""
    ltm = _get_ltm()
    results = ltm.search_memory(
        query=req.query,
        memory_type=req.memory_type,
        tags=req.tags,
        limit=req.limit,
        min_importance=req.min_importance,
    )
    return {"success": True, "total": len(results), "results": results}


@router.get("/ltm/{memory_id}")
async def get_memory(memory_id: str):
    """Get a single memory by ID."""
    ltm = _get_ltm()
    result = ltm.get_memory(memory_id)
    if not result:
        return {"success": False, "error": "Memory not found"}
    return {"success": True, "data": result}


@router.put("/ltm/{memory_id}")
async def update_memory(memory_id: str, req: UpdateMemoryRequest):
    """Update a memory record."""
    ltm = _get_ltm()
    result = ltm.update_memory(
        memory_id=memory_id,
        content=req.content,
        importance=req.importance,
        tags=req.tags,
        metadata=req.metadata,
    )
    if not result:
        return {"success": False, "error": "Memory not found"}
    return {"success": True, "data": result}


@router.delete("/ltm/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory record."""
    ltm = _get_ltm()
    deleted = ltm.forget_memory(memory_id)
    if not deleted:
        return {"success": False, "error": "Memory not found"}
    return {"success": True, "message": "Memory deleted"}


@router.get("/ltm/stats")
async def get_ltm_stats():
    """Get long-term memory statistics."""
    ltm = _get_ltm()
    return {"success": True, "data": ltm.get_stats()}


@router.get("/ltm/types/{memory_type}")
async def get_by_type(memory_type: str, limit: int = 50):
    """Get memories by type."""
    if memory_type not in [t.value for t in MemoryType]:
        return {"success": False, "error": f"Invalid memory type: {memory_type}"}
    ltm = _get_ltm()
    results = ltm.get_by_type(memory_type, limit=limit)
    return {"success": True, "total": len(results), "results": results}


@router.get("/ltm/profile")
async def get_profile():
    """Get user profile memories."""
    ltm = _get_ltm()
    results = ltm.get_profile()
    return {"success": True, "total": len(results), "results": results}


@router.get("/ltm/preferences")
async def get_preferences():
    """Get user preference memories."""
    ltm = _get_ltm()
    results = ltm.get_preferences()
    return {"success": True, "total": len(results), "results": results}
