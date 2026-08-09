"""
Orchestrator API
任务执行、规划、Agent 管理、任务状态查询。
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.memory.service import MemoryService
from app.orchestrator.core import Orchestrator
from app.orchestrator.planner import TaskPlanner
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

_orchestrator: Orchestrator | None = None
_memory: MemoryService | None = None


def _get_memory() -> MemoryService:
    global _memory
    if _memory is None:
        _memory = MemoryService()
    return _memory


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(memory_service=_get_memory())
    return _orchestrator


class TaskRequest(BaseModel):
    task: str
    context: dict | None = None


@router.post("/run")
async def run_task(req: TaskRequest):
    """执行完整任务流程，返回 task_id 和执行结果"""
    orch = _get_orchestrator()
    result = await orch.run(req.task, req.context)

    memory_info = None
    if result.memory_context:
        memory_info = {
            "documents_count": len(result.memory_context.documents),
            "tags": result.memory_context.tags[:10],
            "related_links": result.memory_context.related_links[:10],
        }

    return {
        "task_id": result.task_id,
        "intent": result.intent,
        "status": result.status,
        "total_duration_ms": result.total_duration_ms,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None,
        "memory_context": memory_info,
        "steps_summary": [
            {
                "step_id": r.step_id,
                "status": r.status.value,
                "agent": r.agent_id,
                "duration_ms": r.duration_ms,
                "output": r.output if r.status.value == "success" else None,
                "error": r.error if r.error else None,
            }
            for r in result.steps
        ],
        "final_output": result.final_output,
    }


@router.post("/plan")
async def plan_task(req: TaskRequest):
    """仅规划任务 (不执行)"""
    planner = TaskPlanner()
    plan = planner.plan(req.task)
    return {
        "intent": plan.intent,
        "context_query": plan.context_query,
        "steps": [
            {"id": s.id, "type": s.type.value, "description": s.description,
             "depends_on": s.depends_on, "agent_hint": s.agent_hint}
            for s in plan.steps
        ],
    }


@router.get("/agents")
async def list_agents():
    """获取已注册 Agent 列表"""
    return {"agents": _get_orchestrator().get_agent_list()}


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """查询任务状态"""
    orch = _get_orchestrator()
    record = orch.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return record.to_dict()