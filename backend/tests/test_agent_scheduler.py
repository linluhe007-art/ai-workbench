"""
Phase 4.22 tests - AgentScheduler
Covers: capability matching, health filtering, load balancing, discovery
"""
import pytest

from app.agents.agent_scheduler import AgentScheduler, TaskRequirement, AgentLoadInfo
from app.agents.registry import AgentRegistry
from app.agents.heartbeat import AgentHeartbeat
from app.agents.lifecycle import AgentLifecycleManager, LifecycleState
from app.agents.base import BaseAgent, AgentResult, AgentConfig


class _TestAgent(BaseAgent):
    def __init__(self, agent_id, name="", capabilities=None, score=0):
        self._id = agent_id
        self._name = name or agent_id
        self._caps = capabilities or []
        self.config = AgentConfig(capabilities=self._caps, extra={"score": score})

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Test agent"

    async def execute(self, task, context=None):
        return AgentResult(success=True, output={"task": task})

    def get_capabilities(self):
        return self._caps


@pytest.fixture
def registry():
    r = AgentRegistry()
    r.clear()
    return r


@pytest.fixture
def heartbeat():
    return AgentHeartbeat(timeout_seconds=60.0)


@pytest.fixture
def lifecycle():
    return AgentLifecycleManager()


@pytest.fixture
def scheduler(registry, heartbeat, lifecycle):
    return AgentScheduler(registry, heartbeat, lifecycle)


class TestTaskRequirement:
    def test_default_requirement(self):
        req = TaskRequirement()
        assert req.capabilities == []
        assert req.min_health == "ready"

    def test_requirement_with_caps(self):
        req = TaskRequirement(capabilities=["research", "analysis"])
        assert len(req.capabilities) == 2
        assert "research" in req.capabilities


class TestAgentSchedulerDiscovery:
    def test_discover_empty_registry(self, scheduler):
        agents = scheduler.discover_agents()
        assert agents == []

    def test_discover_registered_agent(self, scheduler, registry):
        agent = _TestAgent("a1", name="researcher", capabilities=["research"])
        registry.register(agent)
        agents = scheduler.discover_agents()
        assert len(agents) == 1
        assert agents[0]["agent_id"] == "a1"
        assert agents[0]["capabilities"] == ["research"]

    def test_discover_multiple_agents(self, scheduler, registry):
        registry.register(_TestAgent("a1", capabilities=["research"]))
        registry.register(_TestAgent("a2", capabilities=["analysis"]))
        agents = scheduler.discover_agents()
        assert len(agents) == 2


class TestAgentSchedulerSelection:
    def test_select_by_capability(self, scheduler, registry):
        registry.register(_TestAgent("a1", capabilities=["research"]))
        registry.register(_TestAgent("a2", capabilities=["analysis"]))
        result = scheduler.select_agent(TaskRequirement(capabilities=["research"]))
        assert result == "a1"

    def test_select_no_match(self, scheduler, registry):
        registry.register(_TestAgent("a1", capabilities=["research"]))
        result = scheduler.select_agent(TaskRequirement(capabilities=["writing"]))
        assert result is None

    def test_select_multiple_match_least_loaded(self, scheduler, registry):
        registry.register(_TestAgent("a1", capabilities=["research"]))
        registry.register(_TestAgent("a2", capabilities=["research"]))
        scheduler.assign_task("a1")
        result = scheduler.select_agent(TaskRequirement(capabilities=["research"]))
        assert result == "a2"

    def test_select_with_health_check(self, scheduler, registry, heartbeat):
        registry.register(_TestAgent("a1", capabilities=["research"]))
        registry.register(_TestAgent("a2", capabilities=["research"]))
        heartbeat.beat("a1")
        result = scheduler.select_agent(TaskRequirement(capabilities=["research"]))
        assert result is not None

    def test_select_matches_all_capabilities(self, scheduler, registry):
        registry.register(_TestAgent("a1", capabilities=["research", "analysis"]))
        registry.register(_TestAgent("a2", capabilities=["research"]))
        result = scheduler.select_agent(TaskRequirement(capabilities=["research", "analysis"]))
        assert result == "a1"


class TestAgentSchedulerLoad:
    def test_assign_and_release(self, scheduler):
        scheduler.assign_task("a1")
        load = scheduler.get_load("a1")
        assert load["active_tasks"] == 1
        scheduler.release_task("a1")
        load = scheduler.get_load("a1")
        assert load["active_tasks"] == 0

    def test_assign_unknown_agent(self, scheduler):
        scheduler.assign_task("unknown")
        load = scheduler.get_load("unknown")
        assert load["active_tasks"] == 1

    def test_release_below_zero(self, scheduler):
        scheduler.release_task("a1")
        load = scheduler.get_load("a1")
        assert load["active_tasks"] == 0

    def test_set_max_concurrent(self, scheduler):
        scheduler.set_max_concurrent("a1", 5)
        load = scheduler.get_load("a1")
        assert load["max_concurrent"] == 5
        assert load["utilization"] == 0.0

    def test_utilization_calculation(self, scheduler):
        scheduler.set_max_concurrent("a1", 4)
        scheduler.assign_task("a1")
        scheduler.assign_task("a1")
        load = scheduler.get_load("a1")
        assert load["utilization"] == 0.5

    def test_get_all_loads(self, scheduler):
        scheduler.assign_task("a1")
        scheduler.assign_task("a2")
        loads = scheduler.get_all_loads()
        assert len(loads) == 2


class TestAgentLoadInfo:
    def test_default_load_info(self):
        info = AgentLoadInfo(agent_id="a1")
        assert info.agent_id == "a1"
        assert info.active_tasks == 0
        assert info.max_concurrent == 3

class TestAgentSchedulerHealthFilter:
    def test_heartbeat_dead_agent_excluded(self, registry, heartbeat):
        scheduler = AgentScheduler(registry, heartbeat, None)
        agent = _TestAgent("a1", capabilities=["research"])
        registry.register(agent)
        # Agent never sent heartbeat - should be considered not alive
        heartbeat.register("a1")
        # Force timeout by using very small timeout
        strict_heartbeat = AgentHeartbeat(timeout_seconds=0.001)
        strict_scheduler = AgentScheduler(registry, strict_heartbeat, None)
        import time
        time.sleep(0.01)
        result = strict_scheduler.select_agent(TaskRequirement(capabilities=["research"]))
        # Without a valid heartbeat, agent should be filtered out
        assert result is None

    def test_lifecycle_ready_agent_included(self, registry, lifecycle):
        scheduler = AgentScheduler(registry, None, lifecycle)
        agent = _TestAgent("a1", capabilities=["research"])
        registry.register(agent)
        lifecycle.register("a1")
        lifecycle._transition("a1", LifecycleState.READY)
        result = scheduler.select_agent(TaskRequirement(capabilities=["research"]))
        assert result == "a1"

    def test_lifecycle_failed_agent_excluded(self, registry, lifecycle):
        scheduler = AgentScheduler(registry, None, lifecycle)
        agent = _TestAgent("a1", capabilities=["research"])
        registry.register(agent)
        lifecycle.register("a1")
        lifecycle._transition("a1", LifecycleState.FAILED, error="crash")
        result = scheduler.select_agent(TaskRequirement(capabilities=["research"]))
        assert result is None


class TestAgentSchedulerDiscoveryAdvanced:
    def test_discover_with_heartbeat(self, scheduler, registry, heartbeat):
        registry.register(_TestAgent("a1", capabilities=["research"]))
        heartbeat.beat("a1")
        agents = scheduler.discover_agents()
        assert agents[0]["alive"] is True
        assert agents[0]["last_heartbeat"] is not None

    def test_discover_with_lifecycle(self, scheduler, registry, lifecycle):
        registry.register(_TestAgent("a1", capabilities=["research"]))
        lifecycle.register("a1")
        lifecycle._transition("a1", LifecycleState.RUNNING)
        agents = scheduler.discover_agents()
        assert agents[0]["lifecycle_state"] == "running"


class TestAgentSchedulerEdgeCases:
    def test_empty_capabilities_selects_all(self, scheduler, registry):
        registry.register(_TestAgent("a1", capabilities=["research"]))
        registry.register(_TestAgent("a2", capabilities=["analysis"]))
        result = scheduler.select_agent(TaskRequirement(capabilities=[]))
        assert result in ("a1", "a2")

    def test_select_from_many(self, scheduler, registry):
        for i in range(5):
            registry.register(_TestAgent(f"a{i}", capabilities=["research"]))
        result = scheduler.select_agent(TaskRequirement(capabilities=["research"]))
        assert result is not None

    def test_max_concurrent_default(self):
        scheduler = AgentScheduler(AgentRegistry())
        scheduler.set_max_concurrent("a1", 10)
        load = scheduler.get_load("a1")
        assert load["max_concurrent"] == 10

    def test_multiple_assign_release(self, scheduler):
        for _ in range(3):
            scheduler.assign_task("a1")
        assert scheduler.get_load("a1")["active_tasks"] == 3
        for _ in range(3):
            scheduler.release_task("a1")
        assert scheduler.get_load("a1")["active_tasks"] == 0