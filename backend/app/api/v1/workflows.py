"""
Workflows API — TaskPlan DAG 可视化数据。

GET /api/v1/tasks/{task_id}/workflow  — 返回任务的 Workflow DAG 结构
"""

from fastapi import APIRouter, HTTPException

from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["workflows"])


def _infer_step_status(trace_events: list[dict], step_id: str) -> dict:
    """从 Trace 事件中推断 step 状态"""
    starts = [e for e in trace_events
              if e.get("event_type") == "start"
              and e.get("metadata", {}).get("step_id") == step_id]
    ends = [e for e in trace_events
            if e.get("event_type") == "end"
            and e.get("metadata", {}).get("step_id") == step_id]
    errors = [e for e in trace_events
              if e.get("event_type") == "error"
              and e.get("metadata", {}).get("step_id") == step_id]

    if errors:
        return {
            "status": "failed",
            "started_at": starts[0]["timestamp"] if starts else None,
            "finished_at": errors[0]["timestamp"],
            "duration": errors[0].get("duration_ms", 0),
            "error": errors[0].get("metadata", {}).get("error", ""),
        }
    if ends:
        return {
            "status": "success",
            "started_at": starts[0]["timestamp"] if starts else None,
            "finished_at": ends[0]["timestamp"],
            "duration": ends[0].get("duration_ms", 0),
        }
    if starts:
        return {
            "status": "running",
            "started_at": starts[0]["timestamp"],
            "finished_at": None,
            "duration": 0,
        }
    return {"status": "pending", "started_at": None, "finished_at": None, "duration": 0}


@router.get("/{task_id}/workflow")
async def get_task_workflow(task_id: str):
    """返回任务的 Workflow DAG 结构"""
    runtime = get_runtime()

    # 验证任务存在
    task_record = runtime.get_task(task_id)
    if task_record is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # 获取 Trace 事件用于推断 step 状态
    trace_events = runtime.trace_collector.get_trace(task_id)
    # get_trace returns list[dict], but we need the raw events for metadata matching
    raw_events = [e.to_dict() for e in runtime.trace_collector._events if e.task_id == task_id]

    # 从执行历史获取 plan 信息
    history = runtime.history.get_history(task_id)

    # 尝试从 TaskLoopManager 的 plan 重建 DAG
    # 使用 Planner 重新生成 plan（与执行时相同的逻辑）
    plan = runtime.planner.plan(task_record.task)

    steps = []
    for step in plan.steps:
        step_info = _infer_step_status(raw_events, step.id)
        steps.append({
            "id": step.id,
            "type": step.type.value,
            "description": step.description,
            "agent": step.agent_hint or "default",
            "depends_on": step.depends_on,
            "status": step_info["status"],
            "started_at": step_info["started_at"],
            "finished_at": step_info["finished_at"],
            "duration": step_info["duration"],
            "error": step_info.get("error"),
        })

    return {
        "task_id": task_id,
        "intent": plan.intent,
        "steps": steps,
        "total_steps": len(steps),
    }