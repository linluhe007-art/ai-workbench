"""Audit API - query audit records."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["audit"])


@router.get("/audit")
async def query_audit_records(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    actor: Optional[str] = Query(None, description="Filter by actor (user/system/agent_id)"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Query audit records with optional filters."""
    runtime = get_runtime()
    records, total = runtime.audit_logger.query(
        task_id=task_id,
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [r.to_dict() for r in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/tasks/{task_id}/audit")
async def get_task_audit_trail(task_id: str):
    """Get the full audit trail for a specific task."""
    runtime = get_runtime()
    record = runtime.get_task(task_id)
    if record is None:
        return {"task_id": task_id, "audit_trail": [], "total": 0, "exists": False}

    trail = runtime.audit_logger.get_audit_trail(task_id)
    return {
        "task_id": task_id,
        "audit_trail": [r.to_dict() for r in trail],
        "total": len(trail),
        "exists": True,
    }


@router.get("/agents/{agent_id}/audit")
async def get_agent_audit(
    agent_id: str,
    limit: int = Query(100, ge=1, le=1000),
):
    """Get audit records for a specific agent."""
    runtime = get_runtime()
    records = runtime.audit_logger.get_agent_audit(agent_id, limit=limit)
    return {
        "agent_id": agent_id,
        "items": [r.to_dict() for r in records],
        "total": len(records),
    }


@router.get("/audit/stats")
async def get_audit_stats():
    """Get audit system statistics."""
    runtime = get_runtime()
    total = runtime.audit_logger.count()
    return {
        "total_records": total,
        "status": "active",
    }


@router.post("/audit/record")
async def record_audit_event(
    actor: str,
    action: str,
    resource_type: str,
    resource_id: str,
    task_id: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """Manually record an audit event (for integration testing)."""
    runtime = get_runtime()
    record = runtime.audit_logger.record(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        task_id=task_id,
        request_id=request_id,
    )
    logger.info("Manual audit record created", record_id=record.id, action=action)
    return record.to_dict()