"""Artifact Search API - global search across all artifacts."""

from datetime import datetime
from fastapi import APIRouter, Query

from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["artifact-search"])


@router.get("/artifacts/search")
async def search_artifacts(
    q: str | None = Query(None, description="Search query (name/content)"),
    type: str | None = Query(None, description="Filter by artifact type"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    task_id: str | None = Query(None, description="Filter by task ID"),
    workspace_id: str | None = Query(None, description="Filter by workspace ID"),
    step_id: str | None = Query(None, description="Filter by step ID"),
    created_after: datetime | None = Query(None, description="Filter by created_after"),
    created_before: datetime | None = Query(None, description="Filter by created_before"),
    sort_by: str = Query("created_at", description="Sort field: created_at|name|type"),
    order: str = Query("desc", description="Sort order: asc|desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Search artifacts with filters, sorting, and pagination."""
    runtime = get_runtime()

    # Validate sort_by
    if sort_by not in ("created_at", "name", "type"):
        sort_by = "created_at"
    if order not in ("asc", "desc"):
        order = "desc"

    items, total = runtime.workspace_manager.search_items(
        query=q,
        artifact_type=type,
        agent_id=agent_id,
        task_id=task_id,
        workspace_id=workspace_id,
        step_id=step_id,
        created_after=created_after,
        created_before=created_before,
        sort_by=sort_by,
        order=order,
        limit=limit,
        offset=offset,
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }