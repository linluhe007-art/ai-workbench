"""
Planning Debug API — 规划调试接口。

POST /api/v1/planning/debug            — 执行 planning 并返回调试信息
GET  /api/v1/planning/debug             — 列出最近 sessions
GET  /api/v1/planning/debug/{session_id} — 获取指定 session
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.runtime.manager import get_runtime
from app.planning.debug import PlanningDebugger
from app.planning.llm_planner import LLMPlanner
from app.orchestrator.llm_provider import MockLLMProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/planning", tags=["planning"])

# 全局 debugger 实例
_debugger: PlanningDebugger | None = None


def _get_debugger() -> PlanningDebugger:
    global _debugger
    if _debugger is None:
        runtime = get_runtime()
        # 创建 LLMPlanner（使用 MockLLM 作为默认 provider）
        llm_provider = MockLLMProvider()
        llm_planner = LLMPlanner(
            llm_provider=llm_provider,
            agent_registry=None,
        )
        _debugger = PlanningDebugger(
            llm_planner=llm_planner,
            agent_registry=None,
        )
    return _debugger


def reset_debugger() -> None:
    """重置 debugger（测试用）"""
    global _debugger
    _debugger = None


class PlanningDebugRequest(BaseModel):
    """规划调试请求"""
    task: str = Field(..., min_length=1, description="任务描述")


@router.post("/debug", status_code=201)
async def debug_planning(req: PlanningDebugRequest):
    """执行 planning 并返回完整调试信息"""
    debugger = _get_debugger()
    session = await debugger.plan(req.task)
    return session.to_dict()


@router.get("/debug")
async def list_debug_sessions():
    """列出最近的 planning sessions"""
    debugger = _get_debugger()
    sessions = debugger.list_sessions()
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/debug/{session_id}")
async def get_debug_session(session_id: str):
    """获取指定 planning session"""
    debugger = _get_debugger()
    session = debugger.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()