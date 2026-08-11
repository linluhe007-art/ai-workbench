"""
Phase 3.19 测试 — Persistence Integration
覆盖：
- RuntimeRepository + AgentRuntime snapshot
- RuntimeRepository + ExecutionHistory snapshot
- RuntimeRepository + TraceCollector snapshot
- RuntimeRepository + ExperienceMemory snapshot
- FileStorage persistence
- Full snapshot-restore cycle
"""

import pytest
import tempfile

from app.storage.memory import MemoryStorage
from app.storage.file import FileStorage
from app.storage.repository import RuntimeRepository
from app.agents.runtime import AgentRuntime
from app.agents.mock_agent import MockAgent
from app.execution.history import ExecutionHistory
from app.observability.collector import TraceCollector
from app.memory.experience import ExperienceMemory


# ── Runtime Snapshot ─────────────────────────────────────────


class TestRuntimeSnapshot:
    async def test_snapshot_agents(self):
        repo = RuntimeRepository(MemoryStorage())
        runtime = AgentRuntime()
        a1 = MockAgent(agent_id="a1")
        a2 = MockAgent(agent_id="a2")
        runtime.register(a1)
        runtime.register(a2)
        await runtime.run_agent("a1", "task1")

        count = await repo.snapshot_from_runtime(runtime)
        assert count == 2

        state = await repo.get_agent_state("a1")
        assert state is not None
        assert state["state"] == "completed"

    async def test_snapshot_empty_runtime(self):
        repo = RuntimeRepository(MemoryStorage())
        runtime = AgentRuntime()
        count = await repo.snapshot_from_runtime(runtime)
        assert count == 0


# ── History Snapshot ─────────────────────────────────────────


class TestHistorySnapshot:
    async def test_snapshot_history(self):
        repo = RuntimeRepository(MemoryStorage())
        history = ExecutionHistory()
        history.record(task_id="t1", iteration=1, plan_intent="test", step_count=2, success=True, status="success")
        history.record(task_id="t1", iteration=2, plan_intent="test", step_count=2, success=False, status="failed")
        history.record(task_id="t2", iteration=1, plan_intent="other", step_count=1, success=True, status="success")

        count = await repo.snapshot_from_history(history)
        assert count == 3

        entries = await repo.get_execution_history("t1")
        assert len(entries) == 2

    async def test_snapshot_empty_history(self):
        repo = RuntimeRepository(MemoryStorage())
        history = ExecutionHistory()
        count = await repo.snapshot_from_history(history)
        assert count == 0


# ── Trace Snapshot ───────────────────────────────────────────


class TestTraceSnapshot:
    async def test_snapshot_collector(self):
        repo = RuntimeRepository(MemoryStorage())
        collector = TraceCollector()
        collector.start("tr1", "task-1", "executor")
        collector.end("tr1", "task-1", "executor", duration_ms=100)
        collector.start("tr2", "task-2", "agent")
        collector.end("tr2", "task-2", "agent", duration_ms=200)

        count = await repo.snapshot_from_collector(collector)
        assert count == 4

        trace1 = await repo.get_trace("tr1")
        assert len(trace1) == 2

    async def test_snapshot_empty_collector(self):
        repo = RuntimeRepository(MemoryStorage())
        collector = TraceCollector()
        count = await repo.snapshot_from_collector(collector)
        assert count == 0


# ── Experience Snapshot ──────────────────────────────────────


class TestExperienceSnapshot:
    async def test_snapshot_experience(self):
        repo = RuntimeRepository(MemoryStorage())
        exp = ExperienceMemory()
        exp.record_experience("research AI", ["a1"], True, {"duration_ms": 500})
        exp.record_experience("write article", ["a2"], False, {"duration_ms": 300})

        count = await repo.snapshot_from_experience(exp)
        assert count == 2

        results = await repo.query_experience("research AI")
        assert len(results) >= 1

    async def test_snapshot_empty_experience(self):
        repo = RuntimeRepository(MemoryStorage())
        exp = ExperienceMemory()
        count = await repo.snapshot_from_experience(exp)
        assert count == 0


# ── FileStorage Integration ──────────────────────────────────


class TestFileStorageIntegration:
    async def test_file_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            repo = RuntimeRepository(FileStorage(d))
            await repo.save_agent_state("a1", {"id": "a1", "state": "completed"})
            await repo.save_execution("t1", 1, {"success": True})
            await repo.save_experience("test", {"pattern": "test"})

            # New repository with same directory
            repo2 = RuntimeRepository(FileStorage(d))
            state = await repo2.get_agent_state("a1")
            assert state["state"] == "completed"
            exec_entry = await repo2.get_execution("t1", 1)
            assert exec_entry["success"] is True

    async def test_full_snapshot_to_file(self):
        with tempfile.TemporaryDirectory() as d:
            repo = RuntimeRepository(FileStorage(d))

            runtime = AgentRuntime()
            runtime.register(MockAgent(agent_id="a1"))
            await runtime.run_agent("a1", "task")

            history = ExecutionHistory()
            history.record(task_id="t1", iteration=1, plan_intent="test", step_count=1, success=True, status="success")

            collector = TraceCollector()
            collector.start("tr1", "t1", "executor")
            collector.end("tr1", "t1", "executor")

            exp = ExperienceMemory()
            exp.record_experience("test", ["a1"], True)

            await repo.snapshot_from_runtime(runtime)
            await repo.snapshot_from_history(history)
            await repo.snapshot_from_collector(collector)
            await repo.snapshot_from_experience(exp)

            # Verify
            agent_states = await repo.list_agent_states()
            assert len(agent_states) == 1
            execs = await repo.list_executions()
            assert "t1" in execs


# ── Cross-Backend Consistency ────────────────────────────────


class TestCrossBackendConsistency:
    async def test_memory_and_file_same_results(self):
        mem_repo = RuntimeRepository(MemoryStorage())
        with tempfile.TemporaryDirectory() as d:
            file_repo = RuntimeRepository(FileStorage(d))

            data = {"key": "value", "nested": [1, 2, 3]}
            await mem_repo.save_agent_state("a1", data)
            await file_repo.save_agent_state("a1", data)

            mem_result = await mem_repo.get_agent_state("a1")
            file_result = await file_repo.get_agent_state("a1")
            assert mem_result == file_result