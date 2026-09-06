"""
Experience API - Phase 4.23
Search, feedback, stats endpoints for the experience learning system.
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.runtime.manager import get_runtime
from app.learning.experience_engine import ExperienceEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/experience", tags=["experience"])


def _get_engine() -> ExperienceEngine:
    """Get or create the experience engine from runtime."""
    runtime = get_runtime()
    if not hasattr(runtime, "_experience_engine") or runtime._experience_engine is None:
        from app.learning.experience_engine import ExperienceEngine
        runtime._experience_engine = ExperienceEngine(runtime.experience)
    return runtime._experience_engine


class FeedbackRequest(BaseModel):
    task_id: str
    task_pattern: str = ""
    rating: float = 0.0
    comment: str = ""


# -- Search --

@router.get("/search")
async def search_experience(
    q: str = Query(default="", description="Search query"),
    success: bool | None = Query(default=None, description="Filter by success"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Search historical experiences by keyword with optional success filter."""
    engine = _get_engine()
    if q:
        results = engine.search(q, limit=limit)
    else:
        results = engine.query("", limit=limit)

    if success is not None:
        results = [r for r in results if r.get("success") == success]

    return {
        "query": q,
        "results": results[:limit],
        "total": len(results),
    }


# -- Feedback --

@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit user feedback on a task execution."""
    engine = _get_engine()
    fb = engine.record_feedback(
        task_id=req.task_id,
        task_pattern=req.task_pattern,
        rating=req.rating,
        comment=req.comment,
    )
    return {
        "success": True,
        "task_id": fb.task_id,
        "rating": fb.rating,
    }


# -- Stats --

@router.get("/stats")
async def get_experience_stats():
    """Get aggregated experience statistics."""
    engine = _get_engine()
    stats = engine.get_stats()
    feedback = engine.get_feedback_stats()

    return {
        "experience": {
            "total_records": stats.total_records,
            "success_count": stats.success_count,
            "failure_count": stats.failure_count,
            "success_rate": round(stats.success_rate, 3),
            "top_patterns": stats.top_patterns[:5],
            "top_agents": stats.top_agents[:5],
            "recent_failures": stats.recent_failures[:5],
        },
        "feedback": feedback,
    }


# -- Recommendations --

@router.get("/recommendations")
async def get_recommendations(
    task_pattern: str = Query(..., description="Task pattern to get recommendations for"),
):
    """Get agent/path recommendations for a task pattern based on history."""
    engine = _get_engine()
    recs = engine.get_recommendations(task_pattern)
    return recs