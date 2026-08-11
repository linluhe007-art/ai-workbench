"""
Phase 3.9.2 测试 — Agent Lifecycle Manager
覆盖：
- LifecycleState 枚举
- LifecycleRecord 状态转换
- AgentLifecycleManager 完整生命周期
- initialize / shutdown / restart
- health_check
- 状态转换合法性校验
- Runtime 集成
"""

import pytest

from app.agents.lifecycle import (
    AgentLifecycleManager,
    LifecycleState,
    LifecycleRecord,
)
from app.agents.runtime import AgentRuntime, AgentState
from app.agents.mock_agent import MockAgent


# ═══════════════════════════════════════════════════════════
# LifecycleState 测试
# ═══════════════════════════════════════════════════════════


class TestLifecycleState:

    def test_states_exist(self):
        assert LifecycleState.CREATED == "created"
        assert LifecycleState.INITIALIZING == "initializing"
        assert LifecycleState.READY == "ready"
        assert LifecycleState.RUNNING == "running"
        assert LifecycleState.STOPPING == "stopping"
        assert LifecycleState.STOPPED == "stopped"
        assert LifecycleState.FAILED == "failed"


class TestLifecycleRecord:

    def test_default_state(self):
        rec = LifecycleRecord(agent_id="a1")
        assert rec.state == LifecycleState.CREATED
        assert rec.error == ""
        assert rec.history == []

    def test_transition(self):
        rec = LifecycleRecord(agent_id="a1")
        rec.transition(LifecycleState.INITIALIZING)
        assert rec.state == LifecycleState.INITIALIZING
        assert len(rec.history) == 1
        assert rec.history[0]["from"] == "created"
        assert rec.history[0]["to"] == "initializing"

    def test_transition_with_error(self):
        rec = LifecycleRecord(agent_id="a1")
        rec.transition(LifecycleState.FAILED, error="connection refused")
        assert rec.state == LifecycleState.FAILED
        assert rec.error == "connection refused"

    def test_multiple_transitions(self):
        rec = LifecycleRecord(agent_id="a1")
        rec.transition(LifecycleState.INITIALIZING)
        rec.transition(LifecycleState.READY)
        rec.transition(LifecycleState.RUNNING)
        assert rec.state == LifecycleState.RUNNING
        assert len(rec.history) == 3


# ═══════════════════════════════════════════════════════════
# AgentLifecycleManager 测试
# ═══════════════════════════════════════════════════════════


class TestLifecycleManagerRegister:

    def test_register(self):
        mgr = AgentLifecycleManager()
        rec = mgr.register("a1")
        assert rec.state == LifecycleState.CREATED
        assert mgr.get_state("a1") == LifecycleState.CREATED

    def test_get_record(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        rec = mgr.get_record("a1")
        assert rec is not None
        assert rec.agent_id == "a1"

    def test_get_record_nonexistent(self):
        mgr = AgentLifecycleManager()
        assert mgr.get_record("ghost") is None

    def test_get_state_nonexistent(self):
        mgr = AgentLifecycleManager()
        assert mgr.get_state("ghost") is None


class TestLifecycleInitialize:

    @pytest.mark.asyncio
    async def test_initialize_without_agent(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")

        ok = await mgr.initialize("a1")
        assert ok is True
        assert mgr.get_state("a1") == LifecycleState.READY

    @pytest.mark.asyncio
    async def test_initialize_with_agent(self):
        mgr = AgentLifecycleManager()
        agent = MockAgent("a1")
        mgr.register("a1")

        ok = await mgr.initialize("a1", agent)
        assert ok is True
        assert mgr.get_state("a1") == LifecycleState.READY
        assert agent.status.value == "online"

    @pytest.mark.asyncio
    async def test_initialize_unregistered(self):
        mgr = AgentLifecycleManager()
        ok = await mgr.initialize("ghost")
        assert ok is False

    @pytest.mark.asyncio
    async def test_initialize_from_ready_fails(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        await mgr.initialize("a1")

        ok = await mgr.initialize("a1")
        assert ok is False

    @pytest.mark.asyncio
    async def test_initialize_from_stopped(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        await mgr.initialize("a1")
        await mgr.shutdown("a1")

        ok = await mgr.initialize("a1")
        assert ok is True
        assert mgr.get_state("a1") == LifecycleState.READY

    @pytest.mark.asyncio
    async def test_initialize_from_failed(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        # Force to FAILED
        mgr._transition("a1", LifecycleState.INITIALIZING)
        mgr._transition("a1", LifecycleState.FAILED, error="boom")

        ok = await mgr.initialize("a1")
        assert ok is True
        assert mgr.get_state("a1") == LifecycleState.READY


class TestLifecycleShutdown:

    @pytest.mark.asyncio
    async def test_shutdown_from_ready(self):
        mgr = AgentLifecycleManager()
        agent = MockAgent("a1")
        mgr.register("a1")
        await mgr.initialize("a1", agent)

        ok = await mgr.shutdown("a1", agent)
        assert ok is True
        assert mgr.get_state("a1") == LifecycleState.STOPPED
        assert agent.status.value == "offline"

    @pytest.mark.asyncio
    async def test_shutdown_from_created_fails(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")

        ok = await mgr.shutdown("a1")
        assert ok is False

    @pytest.mark.asyncio
    async def test_shutdown_from_stopped_fails(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        await mgr.initialize("a1")
        await mgr.shutdown("a1")

        ok = await mgr.shutdown("a1")
        assert ok is False


class TestLifecycleRestart:

    @pytest.mark.asyncio
    async def test_restart(self):
        mgr = AgentLifecycleManager()
        agent = MockAgent("a1")
        mgr.register("a1")
        await mgr.initialize("a1", agent)

        ok = await mgr.restart("a1", agent)
        assert ok is True
        assert mgr.get_state("a1") == LifecycleState.READY

    @pytest.mark.asyncio
    async def test_restart_from_stopped(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        await mgr.initialize("a1")
        await mgr.shutdown("a1")

        ok = await mgr.restart("a1")
        assert ok is True
        assert mgr.get_state("a1") == LifecycleState.READY

    @pytest.mark.asyncio
    async def test_restart_preserves_history(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        await mgr.initialize("a1")
        await mgr.restart("a1")

        rec = mgr.get_record("a1")
        assert len(rec.history) >= 3  # init + shutdown + init


class TestLifecycleTransitionValidation:

    def test_invalid_transition_rejected(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")

        ok = mgr._transition("a1", LifecycleState.RUNNING)
        assert ok is False
        assert mgr.get_state("a1") == LifecycleState.CREATED

    def test_valid_chain(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")

        assert mgr._transition("a1", LifecycleState.INITIALIZING) is True
        assert mgr._transition("a1", LifecycleState.READY) is True
        assert mgr._transition("a1", LifecycleState.RUNNING) is True
        assert mgr._transition("a1", LifecycleState.READY) is True
        assert mgr._transition("a1", LifecycleState.STOPPING) is True
        assert mgr._transition("a1", LifecycleState.STOPPED) is True
        assert mgr.get_state("a1") == LifecycleState.STOPPED

    def test_transition_nonexistent_agent(self):
        mgr = AgentLifecycleManager()
        ok = mgr._transition("ghost", LifecycleState.INITIALIZING)
        assert ok is False


class TestLifecycleHealthCheck:

    @pytest.mark.asyncio
    async def test_health_check_ready(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")

        await mgr.initialize("a1")

        hc = mgr.health_check("a1")
        assert hc["healthy"] is True
        assert hc["state"] == "ready"

    def test_health_check_created_not_healthy(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")

        hc = mgr.health_check("a1")
        assert hc["healthy"] is False
        assert hc["state"] == "created"

    def test_health_check_nonexistent(self):
        mgr = AgentLifecycleManager()
        hc = mgr.health_check("ghost")
        assert hc["healthy"] is False
        assert hc["state"] == "unknown"

    @pytest.mark.asyncio
    async def test_list_agents(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        mgr.register("a2")
        mgr.register("a3")

        await mgr.initialize("a1")

        agents = mgr.list_agents()
        assert len(agents) == 3
        healthy = [a for a in agents if a["healthy"]]
        assert len(healthy) == 1

    @pytest.mark.asyncio
    async def test_list_by_state(self):
        mgr = AgentLifecycleManager()
        mgr.register("a1")
        mgr.register("a2")
        mgr.register("a3")

        await mgr.initialize("a1")

        created = mgr.list_by_state(LifecycleState.CREATED)
        ready = mgr.list_by_state(LifecycleState.READY)
        assert "a2" in created
        assert "a3" in created
        assert "a1" in ready


# ═══════════════════════════════════════════════════════════
# Runtime 集成测试
# ═══════════════════════════════════════════════════════════


class TestRuntimeLifecycleIntegration:

    def test_get_agent_status(self):
        runtime = AgentRuntime()
        agent = MockAgent("a1")
        runtime.register(agent)

        status = runtime.get_agent_status("a1")
        assert status["agent_id"] == "a1"
        assert status["state"] == "idle"

    def test_get_agent_status_nonexistent(self):
        runtime = AgentRuntime()
        status = runtime.get_agent_status("ghost")
        assert status["state"] == "unknown"

    @pytest.mark.asyncio
    async def test_get_agent_status_after_run(self):
        runtime = AgentRuntime()
        agent = MockAgent("a1")
        runtime.register(agent)

        await runtime.run_agent("a1", "test task")

        status = runtime.get_agent_status("a1")
        assert status["state"] == "completed"
        assert status["task"] == "test task"

    def test_list_running_agents_empty(self):
        runtime = AgentRuntime()
        runtime.register(MockAgent("a1"))
        assert runtime.list_running_agents() == []

    @pytest.mark.asyncio
    async def test_list_running_agents(self):
        runtime = AgentRuntime()
        # Simulate running state
        agent = MockAgent("a1")
        runtime.register(agent)
        runtime.set_state("a1", AgentState.RUNNING)

        running = runtime.list_running_agents()
        assert len(running) == 1
        assert running[0]["agent_id"] == "a1"