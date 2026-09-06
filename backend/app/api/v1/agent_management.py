"""
Agent Management API — Agent 详情、能力、健康状态管理。

GET /api/v1/agents/capabilities/all                — 所有能力聚合
GET /api/v1/agents/{agent_id}/capabilities         — Agent 能力详情
GET /api/v1/agents/{agent_id}/health               — Agent 健康状态
GET /api/v1/agents/{agent_id}/history              — Agent 执行历史
"""

from fastapi import APIRouter, HTTPException

from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["agent-management"])


@router.get("/capabilities/all")
async def get_all_capabilities():
    """返回所有 Agent 能力聚合统计"""
    runtime = get_runtime()
    agents = runtime.get_agents()

    cap_map: dict[str, list[str]] = {}
    for agent in agents:
        agent_id = agent.get("id", "")
        caps = agent.get("capabilities", [])
        for cap in caps:
            cap_map.setdefault(cap, []).append(agent_id)

    capabilities = [
        {"name": name, "agents": agent_ids, "count": len(agent_ids)}
        for name, agent_ids in cap_map.items()
    ]
    return {"capabilities": capabilities, "total": len(capabilities)}


@router.get("/{agent_id}/capabilities")
async def get_agent_capabilities(agent_id: str):
    """返回指定 Agent 的能力、元数据和经验统计"""
    runtime = get_runtime()
    agents = runtime.get_agents()

    agent_info = None
    for a in agents:
        if a.get("id") == agent_id:
            agent_info = a
            break

    if agent_info is None:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    caps = agent_info.get("capabilities", [])

    # 从 ExperienceMemory 获取经验统计
    experience = runtime.experience
    all_records = experience._records
    agent_records = [r for r in all_records if agent_id in r.agents]
    task_count = len(agent_records)
    success_count = sum(1 for r in agent_records if r.success)
    success_rate = success_count / task_count if task_count > 0 else 0.0

    return {
        "agent_id": agent_id,
        "capabilities": caps,
        "metadata": agent_info.get("config", {}),
        "experience": {
            "task_count": task_count,
            "success_rate": round(success_rate, 3),
        },
    }


@router.get("/{agent_id}/health")
async def get_agent_health(agent_id: str):
    """返回 Agent 健康状态"""
    runtime = get_runtime()
    status = runtime.runtime.get_agent_status(agent_id)

    if status.get("state") == "unknown":
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # 健康判定：非 FAILED 状态视为 healthy
    state = status.get("state", "unknown")
    healthy = state != "failed"

    return {
        "agent_id": agent_id,
        "healthy": healthy,
        "state": state.upper() if state else "UNKNOWN",
        "last_heartbeat": status.get("completed_at") or status.get("started_at"),
        "error": status.get("error") or None,
    }


@router.get("/{agent_id}/history")
async def get_agent_history(agent_id: str):
    """返回 Agent 执行历史记录"""
    runtime = get_runtime()
    agents = runtime.get_agents()

    # 验证 Agent 存在
    exists = any(a.get("id") == agent_id for a in agents)
    if not exists:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    # 从 ExperienceMemory 获取历史
    records = []
    for rec in runtime.experience._records:
        if agent_id in rec.agents:
            records.append({
                "task_id": rec.task_pattern,
                "success": rec.success,
                "duration": rec.duration_ms,
                "created_at": rec.created_at.isoformat(),
            })

    return {
        "agent_id": agent_id,
        "records": records,
        "total": len(records),
    }