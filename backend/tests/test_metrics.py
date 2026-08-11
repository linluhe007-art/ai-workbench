"""
Phase 3.18 测试 — RuntimeMetrics
覆盖：
- compute 空 collector
- total_tasks 计算
- success_rate 计算
- average_duration 计算
- agent_success_rate 计算
- step_failure_rate 计算
- get_summary
"""

import pytest

from app.observability.collector import TraceCollector
from app.observability.metrics import RuntimeMetrics


# ── RuntimeMetrics ───────────────────────────────────────────


class TestRuntimeMetrics:
    def test_empty_collector(self):
        collector = TraceCollector()
        metrics = RuntimeMetrics(collector).compute()
        assert metrics["total_tasks"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["average_duration_ms"] == 0.0
        assert metrics["agent_runs"] == 0
        assert metrics["agent_success_rate"] == 0.0
        assert metrics["total_steps"] == 0
        assert metrics["step_failure_rate"] == 0.0
        assert metrics["total_errors"] == 0

    def test_single_success_task(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "loop")
        collector.end("t1", "task-1", "loop", duration_ms=500, metadata={"success": True})

        metrics = RuntimeMetrics(collector).compute()
        assert metrics["total_tasks"] == 1
        assert metrics["success_rate"] == 1.0
        assert metrics["average_duration_ms"] == 500.0

    def test_failed_task(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "loop")
        collector.error("t1", "task-1", "loop", error="timeout")
        collector.end("t1", "task-1", "loop", duration_ms=300, metadata={"success": False})

        metrics = RuntimeMetrics(collector).compute()
        assert metrics["total_tasks"] == 1
        assert metrics["success_rate"] == 0.0
        assert metrics["total_errors"] >= 1

    def test_mixed_tasks(self):
        collector = TraceCollector()
        # Task 1: success
        collector.start("t1", "task-1", "loop")
        collector.end("t1", "task-1", "loop", duration_ms=200, metadata={"success": True})
        # Task 2: fail
        collector.start("t2", "task-2", "loop")
        collector.end("t2", "task-2", "loop", duration_ms=100, metadata={"success": False})
        # Task 3: success
        collector.start("t3", "task-3", "loop")
        collector.end("t3", "task-3", "loop", duration_ms=300, metadata={"success": True})

        metrics = RuntimeMetrics(collector).compute()
        assert metrics["total_tasks"] == 3
        assert metrics["success_rate"] == pytest.approx(2 / 3, abs=0.01)

    def test_agent_metrics(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "agent", metadata={"agent_id": "a1"})
        collector.end("t1", "task-1", "agent", metadata={"success": True})
        collector.start("t2", "task-1", "agent", metadata={"agent_id": "a2"})
        collector.error("t2", "task-1", "agent", error="boom")

        metrics = RuntimeMetrics(collector).compute()
        assert metrics["agent_runs"] == 2
        assert metrics["agent_success_rate"] == pytest.approx(0.5, abs=0.01)

    def test_step_metrics(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "executor")
        collector.end("t1", "task-1", "executor", duration_ms=100)
        collector.start("t2", "task-1", "executor")
        collector.error("t2", "task-1", "executor", error="fail")

        metrics = RuntimeMetrics(collector).compute()
        assert metrics["total_steps"] == 2
        assert metrics["step_failure_rate"] == pytest.approx(0.5, abs=0.01)

    def test_average_duration(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "loop")
        collector.end("t1", "task-1", "loop", duration_ms=100, metadata={"success": True})
        collector.start("t2", "task-2", "loop")
        collector.end("t2", "task-2", "loop", duration_ms=300, metadata={"success": True})

        metrics = RuntimeMetrics(collector).compute()
        assert metrics["average_duration_ms"] == 200.0

    def test_get_summary(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "loop")
        collector.end("t1", "task-1", "loop", duration_ms=500, metadata={"success": True})

        summary = RuntimeMetrics(collector).get_summary()
        assert "Tasks: 1" in summary
        assert "100%" in summary

    def test_errors_count(self):
        collector = TraceCollector()
        collector.error("t1", "task-1", "loop", error="e1")
        collector.error("t2", "task-1", "agent", error="e2")
        collector.error("t3", "task-1", "executor", error="e3")

        metrics = RuntimeMetrics(collector).compute()
        assert metrics["total_errors"] == 3

    def test_no_duration_end_events(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "loop")
        collector.end("t1", "task-1", "loop")  # duration_ms=0 default

        metrics = RuntimeMetrics(collector).compute()
        assert metrics["average_duration_ms"] == 0.0