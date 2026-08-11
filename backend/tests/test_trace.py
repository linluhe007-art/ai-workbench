"""
Phase 3.18 测试 — TraceEvent + TraceCollector
覆盖：
- TraceEvent 创建与序列化
- TraceCollector start/end/error/metric
- get_trace / get_by_component / get_errors
- generate_trace_id / generate_task_id
"""

import pytest

from app.observability.trace import TraceEvent
from app.observability.collector import TraceCollector


# ── TraceEvent ──────────────────────────────────────────────


class TestTraceEvent:
    def test_create_trace_event(self):
        event = TraceEvent(
            trace_id="t1",
            task_id="task-1",
            component="executor",
            event_type="start",
        )
        assert event.trace_id == "t1"
        assert event.task_id == "task-1"
        assert event.component == "executor"
        assert event.event_type == "start"
        assert event.duration_ms == 0
        assert event.metadata == {}

    def test_trace_event_with_duration(self):
        event = TraceEvent(
            trace_id="t1",
            task_id="task-1",
            component="agent",
            event_type="end",
            duration_ms=150,
        )
        assert event.duration_ms == 150

    def test_trace_event_with_metadata(self):
        event = TraceEvent(
            trace_id="t1",
            task_id="task-1",
            component="loop",
            event_type="metric",
            metadata={"metric_name": "score", "metric_value": 8.5},
        )
        assert event.metadata["metric_name"] == "score"

    def test_trace_event_to_dict(self):
        event = TraceEvent(
            trace_id="t1",
            task_id="task-1",
            component="executor",
            event_type="start",
            duration_ms=0,
            metadata={"key": "val"},
        )
        d = event.to_dict()
        assert d["trace_id"] == "t1"
        assert d["task_id"] == "task-1"
        assert d["component"] == "executor"
        assert d["event_type"] == "start"
        assert "timestamp" in d
        assert d["metadata"] == {"key": "val"}

    def test_trace_event_timestamp_default(self):
        event = TraceEvent(
            trace_id="t1",
            task_id="task-1",
            component="x",
            event_type="start",
        )
        assert event.timestamp is not None
        assert event.timestamp.tzinfo is not None


# ── TraceCollector ───────────────────────────────────────────


class TestTraceCollector:
    def test_start_event(self):
        collector = TraceCollector()
        event = collector.start("t1", "task-1", "executor")
        assert event.event_type == "start"
        assert event.trace_id == "t1"
        assert collector.total_events == 1

    def test_end_event(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "executor")
        event = collector.end("t1", "task-1", "executor", duration_ms=200)
        assert event.event_type == "end"
        assert event.duration_ms == 200
        assert collector.total_events == 2

    def test_error_event(self):
        collector = TraceCollector()
        event = collector.error("t1", "task-1", "agent", error="timeout")
        assert event.event_type == "error"
        assert event.metadata["error"] == "timeout"

    def test_metric_event(self):
        collector = TraceCollector()
        event = collector.metric("t1", "task-1", "loop", "iteration", 3)
        assert event.event_type == "metric"
        assert event.metadata["metric_name"] == "iteration"
        assert event.metadata["metric_value"] == 3

    def test_get_trace(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "executor")
        collector.end("t1", "task-1", "executor", duration_ms=100)
        collector.start("t2", "task-2", "agent")

        trace = collector.get_trace("task-1")
        assert len(trace) == 2
        assert all(e["task_id"] == "task-1" for e in trace)

    def test_get_trace_empty(self):
        collector = TraceCollector()
        assert collector.get_trace("nonexistent") == []

    def test_get_by_component(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "executor")
        collector.start("t2", "task-2", "agent")
        collector.start("t3", "task-3", "executor")

        events = collector.get_by_component("executor")
        assert len(events) == 2

    def test_get_errors(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "executor")
        collector.error("t1", "task-1", "executor", error="fail1")
        collector.error("t2", "task-2", "agent", error="fail2")

        errors = collector.get_errors()
        assert len(errors) == 2

    def test_get_errors_by_task(self):
        collector = TraceCollector()
        collector.error("t1", "task-1", "executor", error="e1")
        collector.error("t2", "task-2", "agent", error="e2")

        errors = collector.get_errors(task_id="task-1")
        assert len(errors) == 1
        assert errors[0]["metadata"]["error"] == "e1"

    def test_clear(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "executor")
        collector.start("t2", "task-2", "agent")
        assert collector.total_events == 2
        collector.clear()
        assert collector.total_events == 0

    def test_generate_trace_id(self):
        tid1 = TraceCollector.generate_trace_id()
        tid2 = TraceCollector.generate_trace_id()
        assert tid1.startswith("trace-")
        assert tid1 != tid2

    def test_generate_task_id(self):
        tid1 = TraceCollector.generate_task_id()
        tid2 = TraceCollector.generate_task_id()
        assert tid1.startswith("task-")
        assert tid1 != tid2

    def test_start_with_metadata(self):
        collector = TraceCollector()
        event = collector.start("t1", "task-1", "executor", metadata={"key": "val"})
        assert event.metadata["key"] == "val"

    def test_end_with_metadata(self):
        collector = TraceCollector()
        event = collector.end("t1", "task-1", "executor", duration_ms=50, metadata={"k": "v"})
        assert event.metadata["k"] == "v"

    def test_error_with_extra_metadata(self):
        collector = TraceCollector()
        event = collector.error("t1", "task-1", "agent", error="boom", metadata={"extra": 1})
        assert event.metadata["error"] == "boom"
        assert event.metadata["extra"] == 1

    def test_multiple_traces_isolation(self):
        collector = TraceCollector()
        collector.start("t1", "task-a", "executor")
        collector.start("t2", "task-b", "agent")
        collector.end("t1", "task-a", "executor")
        collector.end("t2", "task-b", "agent")

        trace_a = collector.get_trace("task-a")
        trace_b = collector.get_trace("task-b")
        assert len(trace_a) == 2
        assert len(trace_b) == 2