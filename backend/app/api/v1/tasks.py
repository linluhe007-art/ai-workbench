"""
Tasks API — 任务创建与查询。

POST /api/v1/tasks          — 创建并执行任务
GET  /api/v1/tasks           — 列出所有任务
GET  /api/v1/tasks/{task_id} — 查询任务状态
"""

import asyncio

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.runtime.manager import get_runtime, TaskStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    task: str = Field(..., min_length=1, description="任务描述")
    max_iterations: int = Field(default=3, ge=1, le=10, description="最大迭代次数")


class TaskCreateResponse(BaseModel):
    """创建任务响应"""
    task_id: str
    task: str
    status: str


@router.post("", response_model=TaskCreateResponse, status_code=201)
async def create_task(req: TaskCreateRequest, background_tasks: BackgroundTasks):
    """
    创建任务并在后台执行。
    
    返回 task_id，可通过 GET /tasks/{task_id} 查询进度。
    """
    runtime = get_runtime()
    record = runtime.create_task(req.task, req.max_iterations)

    # 后台执行任务
    background_tasks.add_task(_run_task_background, record.task_id, req.max_iterations)

    return TaskCreateResponse(
        task_id=record.task_id,
        task=record.task,
        status=record.status.value,
    )


async def _run_task_background(task_id: str, max_iterations: int):
    """后台执行任务"""
    runtime = get_runtime()
    try:
        await runtime.run_task(task_id, max_iterations)
    except Exception as e:  # noqa: BLE001
        logger.error("Background task failed", task_id=task_id, error=str(e))


@router.get("")
async def list_tasks():
    """列出所有任务"""
    runtime = get_runtime()
    return {"tasks": runtime.list_tasks()}


@router.get("/{task_id}")
async def get_task(task_id: str):
    """查询任务状态"""
    runtime = get_runtime()
    record = runtime.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return record.to_dict()


@router.get("/{task_id}/trace")
async def get_task_trace(task_id: str):
    """获取任务的 Trace 事件链"""
    runtime = get_runtime()
    record = runtime.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")

    trace = runtime.get_trace(task_id)
    return {
        "task_id": task_id,
        "events": trace,
        "total": len(trace),
    }


@router.get("/{task_id}/history")
async def get_task_history(task_id: str):
    """获取任务的执行历史"""
    runtime = get_runtime()
    record = runtime.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")

    history = runtime.get_history(task_id)
    return {
        "task_id": task_id,
        "history": history,
        "total": len(history),
    }