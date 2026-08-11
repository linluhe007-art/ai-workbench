"""
Phase 3.16 测试 — ExecutionHistory
"""

import pytest
from app.execution.history import ExecutionHistory, HistoryEntry


class TestHistoryRecord:

    def test_record(self):
        h = ExecutionHistory()
        entry = h.record(
            task_id="t1", iteration=1, plan_intent="test",
            step_count=2, success=True, status="success",
        )
        assert entry.task_id == "t1"
        assert entry.iteration == 1
        assert entry.success is True

    def test_record_with_failed_steps(self):
        h = ExecutionHistory()
        entry = h.record(
            task_id="t1", iteration=1, plan_intent="test",
            step_count=2, success=False, status="partial",
            failed_steps=["research"],
        )
        assert entry.failed_steps == ["research"]

    def test_total_entries(self):
        h = ExecutionHistory()
        h.record(task_id="t1", iteration=1, plan_intent="", step_count=1, success=True, status="ok")
        h.record(task_id="t1", iteration=2, plan_intent="", step_count=1, success=True, status="ok")
        assert h.total_entries == 2

    def test_clear(self):
        h = ExecutionHistory()
        h.record(task_id="t1", iteration=1, plan_intent="", step_count=1, success=True, status="ok")
        h.clear()
        assert h.total_entries == 0

    def test_generate_task_id(self):
        tid1 = ExecutionHistory.generate_task_id()
        tid2 = ExecutionHistory.generate_task_id()
        assert tid1 != tid2
        assert tid1.startswith("task-")


class TestHistoryQuery:

    def test_get_history(self):
        h = ExecutionHistory()
        h.record(task_id="t1", iteration=1, plan_intent="", step_count=1, success=True, status="ok")
        h.record(task_id="t1", iteration=2, plan_intent="", step_count=1, success=False, status="fail")
        h.record(task_id="t2", iteration=1, plan_intent="", step_count=1, success=True, status="ok")

        history = h.get_history("t1")
        assert len(history) == 2

    def test_get_last(self):
        h = ExecutionHistory()
        h.record(task_id="t1", iteration=1, plan_intent="", step_count=1, success=True, status="ok")
        h.record(task_id="t1", iteration=2, plan_intent="", step_count=1, success=False, status="fail")

        last = h.get_last("t1")
        assert last.iteration == 2
        assert last.success is False

    def test_get_last_empty(self):
        h = ExecutionHistory()
        assert h.get_last("ghost") is None

    def test_get_iteration_count(self):
        h = ExecutionHistory()
        h.record(task_id="t1", iteration=1, plan_intent="", step_count=1, success=True, status="ok")
        h.record(task_id="t1", iteration=2, plan_intent="", step_count=1, success=True, status="ok")
        assert h.get_iteration_count("t1") == 2

    def test_get_success_rate(self):
        h = ExecutionHistory()
        h.record(task_id="t1", iteration=1, plan_intent="", step_count=1, success=False, status="fail")
        h.record(task_id="t1", iteration=2, plan_intent="", step_count=1, success=True, status="ok")
        assert h.get_success_rate("t1") == 0.5

    def test_success_rate_empty(self):
        h = ExecutionHistory()
        assert h.get_success_rate("ghost") == 0.0


class TestHistoryEntry:

    def test_to_dict(self):
        h = ExecutionHistory()
        entry = h.record(
            task_id="t1", iteration=1, plan_intent="test",
            step_count=2, success=True, status="success",
            duration_ms=100,
        )
        d = entry.to_dict()
        assert d["task_id"] == "t1"
        assert d["iteration"] == 1
        assert d["duration_ms"] == 100
        assert "created_at" in d

class TestHistoryEdgeCases:

    def test_multiple_tasks_isolated(self):
        h = ExecutionHistory()
        h.record(task_id="t1", iteration=1, plan_intent="", step_count=1, success=True, status="ok")
        h.record(task_id="t2", iteration=1, plan_intent="", step_count=1, success=False, status="fail")
        assert h.get_iteration_count("t1") == 1
        assert h.get_iteration_count("t2") == 1

    def test_entry_fields(self):
        h = ExecutionHistory()
        entry = h.record(
            task_id="t1", iteration=1, plan_intent="研究AI",
            step_count=3, success=False, status="partial",
            duration_ms=500, failed_steps=["writing"], error="boom",
        )
        assert entry.duration_ms == 500
        assert entry.error == "boom"
        assert entry.plan_intent == "研究AI"

    def test_get_history_empty(self):
        h = ExecutionHistory()
        assert h.get_history("ghost") == []