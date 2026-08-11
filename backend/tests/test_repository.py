"""
Phase 3.19 测试 — RuntimeRepository
覆盖：
- Agent state save/get/list/delete
- Execution save/get/history
- Trace save/get/batch
- Experience save/query
"""

import pytest

from app.storage.memory import MemoryStorage
from app.storage.repository import RuntimeRepository


# ── Agent State ──────────────────────────────────────────────


class TestRepositoryAgentState:
    async def test_save_and_get_agent_state(self):
        repo = RuntimeRepository(MemoryStorage())
        state = {"agent_id": "mock-1", "state": "idle", "task": ""}
        await repo.save_agent_state("mock-1", state)
        result = await repo.get_agent_state("mock-1")
        assert result["agent_id"] == "mock-1"

    async def test_get_nonexistent_agent(self):
        repo = RuntimeRepository(MemoryStorage())
        result = await repo.get_agent_state("missing")
        assert result is None

    async def test_list_agent_states(self):
        repo = RuntimeRepository(MemoryStorage())
        await repo.save_agent_state("a1", {"id": "a1", "state": "idle"})
        await repo.save_agent_state("a2", {"id": "a2", "state": "running"})
        states = await repo.list_agent_states()
        assert len(states) == 2

    async def test_delete_agent_state(self):
        repo = RuntimeRepository(MemoryStorage())
        await repo.save_agent_state("a1", {"id": "a1"})
        deleted = await repo.delete_agent_state("a1")
        assert deleted is True
        assert (await repo.get_agent_state("a1")) is None


# ── Execution History ────────────────────────────────────────


class TestRepositoryExecution:
    async def test_save_and_get_execution(self):
        repo = RuntimeRepository(MemoryStorage())
        entry = {"task_id": "t1", "iteration": 1, "success": True}
        await repo.save_execution("t1", 1, entry)
        result = await repo.get_execution("t1", 1)
        assert result["success"] is True

    async def test_get_nonexistent_execution(self):
        repo = RuntimeRepository(MemoryStorage())
        result = await repo.get_execution("t1", 1)
        assert result is None

    async def test_get_execution_history(self):
        repo = RuntimeRepository(MemoryStorage())
        await repo.save_execution("t1", 1, {"iter": 1, "success": False})
        await repo.save_execution("t1", 2, {"iter": 2, "success": True})
        await repo.save_execution("t2", 1, {"iter": 1, "success": True})
        history = await repo.get_execution_history("t1")
        assert len(history) == 2

    async def test_list_executions(self):
        repo = RuntimeRepository(MemoryStorage())
        await repo.save_execution("t1", 1, {})
        await repo.save_execution("t2", 1, {})
        task_ids = await repo.list_executions()
        assert set(task_ids) == {"t1", "t2"}


# ── Trace Events ─────────────────────────────────────────────


class TestRepositoryTrace:
    async def test_save_and_get_trace(self):
        repo = RuntimeRepository(MemoryStorage())
        event = {"trace_id": "tr1", "event_type": "start", "component": "executor"}
        await repo.save_trace("tr1", 0, event)
        events = await repo.get_trace("tr1")
        assert len(events) == 1
        assert events[0]["event_type"] == "start"

    async def test_get_nonexistent_trace(self):
        repo = RuntimeRepository(MemoryStorage())
        events = await repo.get_trace("missing")
        assert events == []

    async def test_save_trace_events_batch(self):
        repo = RuntimeRepository(MemoryStorage())
        events = [
            {"trace_id": "tr1", "event_type": "start", "component": "executor"},
            {"trace_id": "tr1", "event_type": "end", "component": "executor"},
            {"trace_id": "tr1", "event_type": "error", "component": "agent"},
        ]
        count = await repo.save_trace_events("tr1", events)
        assert count == 3
        result = await repo.get_trace("tr1")
        assert len(result) == 3

    async def test_trace_ordering(self):
        repo = RuntimeRepository(MemoryStorage())
        events = [{"idx": i} for i in range(5)]
        await repo.save_trace_events("tr1", events)
        result = await repo.get_trace("tr1")
        indices = [e["idx"] for e in result]
        assert indices == [0, 1, 2, 3, 4]


# ── Experience Records ───────────────────────────────────────


class TestRepositoryExperience:
    async def test_save_and_query_experience(self):
        repo = RuntimeRepository(MemoryStorage())
        rec = {"task_pattern": "research AI", "agents": ["a1"], "success": True}
        await repo.save_experience("research AI", rec)
        results = await repo.query_experience("research AI")
        assert len(results) == 1
        assert results[0]["task_pattern"] == "research AI"

    async def test_query_nonexistent(self):
        repo = RuntimeRepository(MemoryStorage())
        results = await repo.query_experience("nothing")
        assert results == []

    async def test_list_experiences(self):
        repo = RuntimeRepository(MemoryStorage())
        await repo.save_experience("p1", {"pattern": "p1"})
        await repo.save_experience("p2", {"pattern": "p2"})
        keys = await repo.list_experiences()
        assert len(keys) == 2

    async def test_experience_returns_key(self):
        repo = RuntimeRepository(MemoryStorage())
        key = await repo.save_experience("test", {"data": 1})
        assert key.startswith("exp:test:")