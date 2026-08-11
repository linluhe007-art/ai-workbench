"""
Agents API — Agent 注册列表与状态查询。

GET /api/v1/agents           — 列出所有 Agent
GET  /api/v1/agents/{id}     — 查询单个 Agent 详情
"""

from fastapi import APIRouter, HTTPException

from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("")
async def list_agents():
    """列出所有已注册 Agent 及其状态"""
    runtime = get_runtime()
    agents = runtime.get_agents()
    return {
        "agents": agents,
        "total": len(agents),
    }


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """查询指定 Agent 详情"""
    runtime = get_runtime()
    agents = runtime.get_agents()
    for agent in agents:
        if agent.get("id") == agent_id:
            return agent
    raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")


@router.get("/status/runtime")
async def runtime_status():
    """获取运行时状态概览"""
    runtime = get_runtime()
    return {
        "agents_count": len(runtime.get_agents()),
        "tasks_count": len(runtime.list_tasks()),
        "metrics": runtime.get_metrics(),
    }