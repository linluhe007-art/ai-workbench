"""
Tasks API - task creation, query, lifecycle control, and events.
"""

import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field

from app.runtime.manager import get_runtime, TaskStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    task: str = Field(..., min_length=1, description="Task description")
    max_iterations: int = Field(default=3, ge=1, le=10)
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)


class TaskCreateResponse(BaseModel):
    task_id: str
    task: str
    status: str


@router.post("", response_model=TaskCreateResponse, status_code=201)
async def create_task(req: TaskCreateRequest, background_tasks: BackgroundTasks):
    """Create task and submit to queue."""
    runtime = get_runtime()
    record = runtime.create_task(req.task, req.max_iterations)
    if req.timeout_seconds:
        record.timeout_seconds = req.timeout_seconds
    background_tasks.add_task(_submit_task_background, record.task_id, req.max_iterations)
    return TaskCreateResponse(task_id=record.task_id, task=record.task, status=record.status.value)


async def _submit_task_background(task_id: str, max_iterations: int):
    runtime = get_runtime()
    try:
        await runtime.submit_task(task_id, max_iterations)
    except Exception as e:  # noqa: BLE001
        logger.error("Background task submit failed", task_id=task_id, error=str(e))


@router.get("/queue/status")
async def queue_status():
    """Get task queue status."""
    return get_runtime().get_queue_status()


@router.get("")
async def list_tasks():
    """List all tasks."""
    return {"tasks": get_runtime().list_tasks()}


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get task status."""
    record = get_runtime().get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return record.to_dict()


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a task."""
    record = get_runtime().get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    result = await get_runtime().cancel_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Cannot cancel"))
    return result


@router.post("/{task_id}/pause")
async def pause_task(task_id: str):
    """Pause a running task."""
    record = get_runtime().get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    result = await get_runtime().pause_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Cannot pause"))
    return result


@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    """Resume a paused task."""
    record = get_runtime().get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    result = await get_runtime().resume_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Cannot resume"))
    return result


@router.post("/{task_id}/retry")
async def retry_task(task_id: str):
    """Retry a failed/cancelled/timeout task."""
    record = get_runtime().get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    result = await get_runtime().retry_task(task_id)
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("error", "Cannot retry"))
    return result


@router.get("/{task_id}/events")
async def get_task_events(task_id: str, since_sequence: int = 0):
    """Get task events with optional sequence filter for replay."""
    runtime = get_runtime()
    record = runtime.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    events = runtime.get_task_events(task_id, since_sequence=since_sequence)
    return {
        "task_id": task_id,
        "events": events,
        "total": len(events),
        "last_sequence": runtime.event_store.get_last_sequence(task_id),
    }


@router.get("/{task_id}/trace")
async def get_task_trace(task_id: str):
    """Get task trace events."""
    record = get_runtime().get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    trace = get_runtime().get_trace(task_id)
    return {"task_id": task_id, "events": trace, "total": len(trace)}


@router.get("/{task_id}/history")
async def get_task_history(task_id: str):
    """Get task execution history."""
    record = get_runtime().get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    history = get_runtime().get_history(task_id)
    return {"task_id": task_id, "history": history, "total": len(history)}