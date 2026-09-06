"""
Agent Lifecycle API - Phase 4.22
Management endpoints: registry, heartbeat, enable/disable, runtime status.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["agent-lifecycle"])


class AgentRegisterRequest(BaseModel):
    agent_id: str
    capabilities: list[str] = []
    metadata: dict | None = None


class HeartbeatRequest(BaseModel):
    agent_id: str


# -- Registry --

@router.get("/registry")
async def get_registry():
    """List all registered agents with full lifecycle data."""
    runtime = get_runtime()
    agents = runtime.runtime.list_agents()
    return {"agents": agents, "total": len(agents)}


@router.post("/register")
async def register_agent(req: AgentRegisterRequest):
    """Register a new agent dynamically."""
    runtime = get_runtime()

    existing = runtime.runtime.get(req.agent_id)
    if existing:
        return {
            "success": True,
            "agent_id": req.agent_id,
            "message": "Agent already registered",
        }

    from app.agents.base import BaseAgent, AgentConfig

    config = AgentConfig(
        capabilities=req.capabilities,
        metadata=req.metadata or {},
    )

    class DynamicAgent(BaseAgent):
        @property
        def name(self) -> str:
            return req.agent_id

        @property
        def description(self) -> str:
            return "Dynamically registered agent"

        async def execute(self, task: str, context: dict | None = None) -> "AgentResult":
            from app.agents.base import AgentResult
            return AgentResult(success=True, output={"task": task})

        def get_capabilities(self) -> list[str]:
            return req.capabilities

    agent = DynamicAgent()
    agent.config = config
    agent.id = req.agent_id

    runtime.runtime.register(agent)

    logger.info("Agent registered dynamically", agent_id=req.agent_id)
    return {
        "success": True,
        "agent_id": req.agent_id,
        "capabilities": req.capabilities,
    }


# -- Heartbeat --

@router.post("/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str):
    """Record a heartbeat for an agent."""
    runtime = get_runtime()

    existing = runtime.runtime.get(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    if hasattr(runtime.runtime, "_heartbeat") and runtime.runtime._heartbeat:
        runtime.runtime._heartbeat.beat(agent_id)

    return {
        "agent_id": agent_id,
        "alive": True,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


# -- Enable / Disable --

@router.post("/{agent_id}/disable")
async def disable_agent(agent_id: str):
    """Disable an agent (mark as disabled, stop accepting tasks)."""
    runtime = get_runtime()

    existing = runtime.runtime.get(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    if hasattr(existing, "config"):
        existing.config.enabled = False

    logger.info("Agent disabled", agent_id=agent_id)
    return {"success": True, "agent_id": agent_id, "enabled": False}


@router.post("/{agent_id}/enable")
async def enable_agent(agent_id: str):
    """Enable a previously disabled agent."""
    runtime = get_runtime()

    existing = runtime.runtime.get(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    if hasattr(existing, "config"):
        existing.config.enabled = True

    logger.info("Agent enabled", agent_id=agent_id)
    return {"success": True, "agent_id": agent_id, "enabled": True}


# -- Runtime --

@router.get("/{agent_id}/runtime")
async def get_agent_runtime(agent_id: str):
    """Get detailed runtime information for an agent."""
    runtime = get_runtime()

    existing = runtime.runtime.get(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")

    status = runtime.runtime.get_agent_status(agent_id)
    load_info = {"active_tasks": 0, "max_concurrent": 3}

    return {
        "agent_id": agent_id,
        "name": existing.name if hasattr(existing, "name") else agent_id,
        "state": status.get("state", "unknown"),
        "task": status.get("task", ""),
        "started_at": status.get("started_at"),
        "completed_at": status.get("completed_at"),
        "error": status.get("error", ""),
        "load": load_info,
        "capabilities": getattr(existing, "get_capabilities", lambda: [])() if hasattr(existing, "get_capabilities") else [],
    }


# -- Scheduler status --

@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get scheduler overview: all agents with load and health."""
    runtime = get_runtime()
    agents = runtime.runtime.list_agents()

    result = []
    for agent in agents:
        agent_id = agent.get("id", "")
        status = runtime.runtime.get_agent_status(agent_id)
        result.append({
            "agent_id": agent_id,
            "name": agent.get("name", ""),
            "state": status.get("state", "unknown"),
            "capabilities": agent.get("capabilities", []),
            "enabled": agent.get("config", {}).get("enabled", True),
        })

    return {"agents": result, "total": len(result)}