"""
Memory API
提供知识库查询、搜索、索引和统计接口。
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.memory.service import MemoryService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])

_memory: MemoryService | None = None


def _get_memory() -> MemoryService:
    global _memory
    if _memory is None:
        _memory = MemoryService()
    return _memory


class SearchRequest(BaseModel):
    keyword: str
    limit: int = 10


@router.get("/stats")
async def get_stats():
    """获取知识库统计信息"""
    mem = _get_memory()
    try:
        stats = mem.get_stats()
        return {"status": "ok", "data": stats}
    except Exception as e:  # noqa: BLE001 — API error returns structured response
        logger.error("Memory stats failed", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/search")
async def search(req: SearchRequest):
    """基于索引的关键词搜索"""
    mem = _get_memory()
    results = mem.search(req.keyword, limit=req.limit)
    return {
        "keyword": req.keyword,
        "total": len(results),
        "results": results,
    }


@router.get("/context")
async def get_context(q: str = Query(..., description="查询主题"), max_chars: int = 3000):
    """获取结构化记忆上下文"""
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
    """
    刷新知识库索引
    full=true: 全量扫描
    full=false: 增量扫描 (只更新变化文件)
    """
    mem = _get_memory()
    if full:
        count = mem.refresh()
    else:
        count = mem.incremental_refresh()
    return {"status": "ok", "files_updated": count, "mode": "full" if full else "incremental"}