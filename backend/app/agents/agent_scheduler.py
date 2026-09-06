"""
AgentScheduler - Agent selection with capability matching, load balancing, health checking.
Phase 4.22: Scheduler uses existing AgentRegistry, AgentHeartbeat, and AgentLifecycleManager.
"""
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry
    from app.agents.heartbeat import AgentHeartbeat
    from app.agents.lifecycle import AgentLifecycleManager

logger = get_logger(__name__)


@dataclass
class TaskRequirement:
    """Represents what a task needs from an agent."""
    capabilities: list[str] = field(default_factory=list)
    min_health: str = "ready"
    priority: int = 0


@dataclass
class AgentLoadInfo:
    """Tracks agent load for balancing."""
    agent_id: str
    active_tasks: int = 0
    max_concurrent: int = 3


class AgentScheduler:
    """
    Agent selection strategy combining:
    1. Capability matching - only agents with required capabilities
    2. Health checking - only healthy agents
    3. Load balancing - prefer least loaded agent

    Usage:
        scheduler = AgentScheduler(registry, heartbeat, lifecycle)
        agent_id = scheduler.select_agent(TaskRequirement(capabilities=["research"]))
    """

    def __init__(
        self,
        registry: "AgentRegistry",
        heartbeat: "AgentHeartbeat | None" = None,
        lifecycle: "AgentLifecycleManager | None" = None,
    ):
        self._registry = registry
        self._heartbeat = heartbeat
        self._lifecycle = lifecycle
        self._load: dict[str, AgentLoadInfo] = {}

    # -- Agent discovery --

    def discover_agents(self) -> list[dict]:
        """Return all registered agents with their status, load, and capabilities."""
        agents = self._registry.list_agents()
        result = []
        for agent in agents:
            agent_id = agent.get("id", "")
            info = {
                "agent_id": agent_id,
                "name": agent.get("name", ""),
                "capabilities": agent.get("capabilities", []),
                "enabled": agent.get("enabled", True),
            }

            # Health status
            if self._heartbeat:
                hb = self._heartbeat.get_status(agent_id)
                info["alive"] = hb["alive"]
                info["last_heartbeat"] = hb["last_seen"]
            else:
                info["alive"] = True
                info["last_heartbeat"] = None

            # Lifecycle state
            if self._lifecycle:
                lc_state = self._lifecycle.get_state(agent_id)
                info["lifecycle_state"] = lc_state.value if lc_state else "unknown"
            else:
                info["lifecycle_state"] = "unknown"

            # Load
            load = self._load.get(agent_id, AgentLoadInfo(agent_id=agent_id))
            info["active_tasks"] = load.active_tasks
            info["max_concurrent"] = load.max_concurrent

            result.append(info)
        return result

    # -- Agent selection --

    def select_agent(self, requirement: TaskRequirement) -> str | None:
        """
        Select the best agent for a task requirement.

        Steps:
        1. Filter by capabilities
        2. Filter by health (alive + lifecycle state)
        3. Sort by load (least busy first)
        """
        candidates = self._candidates_by_capability(requirement.capabilities)
        if not candidates:
            logger.debug("No agent matches capability", capabilities=requirement.capabilities)
            return None

        healthy = self._filter_healthy(candidates, requirement.min_health)
        if not healthy:
            logger.debug("No healthy agent available", candidates=len(candidates))
            return None

        selected = self._least_loaded(healthy)
        logger.info(
            "Agent selected by scheduler",
            selected=selected,
            requirement_caps=requirement.capabilities,
            candidates=len(candidates),
        )
        return selected

    # -- Load management --

    def assign_task(self, agent_id: str) -> None:
        """Increment active task count for an agent."""
        if agent_id not in self._load:
            self._load[agent_id] = AgentLoadInfo(agent_id=agent_id)
        self._load[agent_id].active_tasks += 1

    def release_task(self, agent_id: str) -> None:
        """Decrement active task count for an agent."""
        if agent_id in self._load:
            self._load[agent_id].active_tasks = max(0, self._load[agent_id].active_tasks - 1)

    def set_max_concurrent(self, agent_id: str, max_concurrent: int) -> None:
        """Set the maximum concurrent tasks for an agent."""
        if agent_id not in self._load:
            self._load[agent_id] = AgentLoadInfo(agent_id=agent_id)
        self._load[agent_id].max_concurrent = max_concurrent

    def get_load(self, agent_id: str) -> dict:
        """Get current load info for an agent."""
        load = self._load.get(agent_id, AgentLoadInfo(agent_id=agent_id))
        return {
            "agent_id": agent_id,
            "active_tasks": load.active_tasks,
            "max_concurrent": load.max_concurrent,
            "utilization": load.active_tasks / load.max_concurrent if load.max_concurrent > 0 else 0,
        }

    def get_all_loads(self) -> list[dict]:
        """Get load info for all tracked agents."""
        return [self.get_load(aid) for aid in self._load]

    # -- Internal helpers --

    def _candidates_by_capability(self, capabilities: list[str]) -> list[str]:
        """Find agents matching ALL required capabilities."""
        if not capabilities:
            agents = self._registry.list_agents()
            return [a["id"] for a in agents]

        candidates: set[str] | None = None
        for cap in capabilities:
            matching = set(self._registry.get_agents_by_capability(cap))
            if candidates is None:
                candidates = matching
            else:
                candidates &= matching
            if not candidates:
                return []
        return list(candidates) if candidates else []

    def _filter_healthy(self, agent_ids: list[str], min_health: str) -> list[str]:
        """Filter agents by health and lifecycle state."""
        healthy = []
        for agent_id in agent_ids:
            # Heartbeat check
            if self._heartbeat:
                if not self._heartbeat.is_alive(agent_id):
                    continue

            # Lifecycle state check
            if self._lifecycle:
                state = self._lifecycle.get_state(agent_id)
                if state is None:
                    continue
                healthy_states = {"ready", "running", "idle"}
                if state.value not in healthy_states:
                    continue

            healthy.append(agent_id)
        return healthy

    def _least_loaded(self, agent_ids: list[str]) -> str:
        """Select agent with lowest active_task count."""
        def load_key(aid: str) -> float:
            load = self._load.get(aid, AgentLoadInfo(agent_id=aid))
            return load.active_tasks
        return min(agent_ids, key=load_key)