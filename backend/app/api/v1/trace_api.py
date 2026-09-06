"""Decision Trace API - Phase 5.11"""
from fastapi import APIRouter, Query

from app.intelligence.trace.decision_store import get_trace_store
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence-trace"])


@router.get("/traces")
async def get_traces(
    task_id: str = Query(default=""),
    user_id: str = Query(default=""),
    component: str = Query(default=""),
    trace_type: str = Query(default=""),
    limit: int = Query(default=100),
    offset: int = Query(default=0),
):
    """Query decision traces with optional filters."""
    store = get_trace_store()
    traces = store.query(
        task_id=task_id or None,
        user_id=user_id or None,
        component=component or None,
        trace_type=trace_type or None,
        limit=min(limit, 500),
        offset=offset,
    )
    return {"success": True, "traces": traces, "total": len(traces), "limit": limit, "offset": offset}

@router.get("/tasks/{task_id}/decision-trace")
async def get_task_decision_trace(task_id: str):
    """Get the full decision trace for a specific task."""
    store = get_trace_store()
    traces = store.get_by_task(task_id)
    return {"success": True, "task_id": task_id, "traces": traces, "total": len(traces)}
