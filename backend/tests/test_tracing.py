"""
Phase 4.21 tests - TraceContext
Covers: TraceContext creation, start_span/end_span, span hierarchy,
        duration calculation, to_dict, ContextVar isolation
"""
import pytest
from app.observability.tracing_context import (
    TraceContext,
    Span,
    get_current_trace,
    set_current_trace,
    clear_current_trace,
)


class TestSpan:
    def test_span_creation(self):
        span = Span(
            span_id="span-1",
            trace_id="trace-1",
            name="test_span",
            component="test",
        )
        assert span.span_id == "span-1"
        assert span.trace_id == "trace-1"
        assert span.name == "test_span"
        assert span.parent_span_id == ""
        assert span.status == "ok"
        assert span.events == []

    def test_span_to_dict(self):
        span = Span(
            span_id="span-1",
            trace_id="trace-1",
            parent_span_id="parent-1",
            name="test",
            component="test_comp",
            start_time="2024-01-01T00:00:00",
            end_time="2024-01-01T00:00:01",
            duration_ms=1000.0,
            status="ok",
            metadata={"key": "value"},
        )
        d = span.to_dict()
        assert d["span_id"] == "span-1"
        assert d["trace_id"] == "trace-1"
        assert d["parent_span_id"] == "parent-1"
        assert d["name"] == "test"
        assert d["component"] == "test_comp"
        assert d["duration_ms"] == 1000.0
        assert d["status"] == "ok"
        assert d["metadata"] == {"key": "value"}

    def test_span_default_values(self):
        span = Span(span_id="s1", trace_id="t1")
        assert span.parent_span_id == ""
        assert span.name == ""
        assert span.component == ""
        assert span.start_time == ""
        assert span.end_time == ""
        assert span.duration_ms == 0.0
        assert span.status == "ok"
        assert span.metadata == {}
        assert span.events == []


class TestTraceContext:
    def test_creates_trace_id(self):
        trace = TraceContext()
        assert trace.trace_id
        assert trace.trace_id.startswith("trace-")

    def test_uses_provided_trace_id(self):
        trace = TraceContext(trace_id="my-custom-trace")
        assert trace.trace_id == "my-custom-trace"

    def test_start_span(self):
        trace = TraceContext()
        span = trace.start_span("api_request", "http")
        assert span.name == "api_request"
        assert span.component == "http"
        assert span.trace_id == trace.trace_id
        assert span.span_id
        assert span.start_time

    def test_start_span_with_metadata(self):
        trace = TraceContext()
        span = trace.start_span("task_exec", "executor", metadata={"task_id": "t1"})
        assert span.metadata == {"task_id": "t1"}

    def test_span_parent_hierarchy(self):
        trace = TraceContext()
        parent = trace.start_span("parent", "comp1")
        child = trace.start_span("child", "comp2")
        assert child.parent_span_id == parent.span_id

    def test_end_span(self):
        trace = TraceContext()
        span = trace.start_span("test", "comp")
        trace.end_span(span)
        assert span.end_time
        assert span.duration_ms >= 0
        assert span.status == "ok"

    def test_end_span_with_status(self):
        trace = TraceContext()
        span = trace.start_span("test", "comp")
        trace.end_span(span, status="error")
        assert span.status == "error"

    def test_end_span_restores_parent(self):
        trace = TraceContext()
        parent = trace.start_span("parent", "comp")
        child = trace.start_span("child", "comp")
        trace.end_span(child)
        grandchild = trace.start_span("grandchild", "comp")
        assert grandchild.parent_span_id == parent.span_id

    def test_add_event(self):
        trace = TraceContext()
        span = trace.start_span("test", "comp")
        trace.add_event(span, "checkpoint", {"step": 1})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "checkpoint"
        assert span.events[0]["data"] == {"step": 1}

    def test_get_root_span(self):
        trace = TraceContext()
        span1 = trace.start_span("first", "comp")
        span2 = trace.start_span("second", "comp")
        root = trace.get_root_span()
        assert root.span_id == span1.span_id

    def test_get_root_span_empty(self):
        trace = TraceContext()
        assert trace.get_root_span() is None

    def test_get_total_duration(self):
        trace = TraceContext()
        duration = trace.get_total_duration_ms()
        assert duration >= 0

    def test_to_dict(self):
        trace = TraceContext()
        trace.start_span("api", "http")
        d = trace.to_dict()
        assert "trace_id" in d
        assert "spans" in d
        assert "total_duration_ms" in d
        assert "span_count" in d
        assert d["span_count"] == 1

    def test_to_dict_multiple_spans(self):
        trace = TraceContext()
        trace.start_span("api", "http")
        trace.start_span("db", "postgres")
        d = trace.to_dict()
        assert d["span_count"] == 2


class TestTraceContextVar:
    def test_get_current_trace_none(self):
        clear_current_trace()
        assert get_current_trace() is None

    def test_set_and_get_current_trace(self):
        trace = TraceContext(trace_id="test-trace")
        set_current_trace(trace)
        assert get_current_trace() is trace
        assert get_current_trace().trace_id == "test-trace"

    def test_clear_current_trace(self):
        trace = TraceContext()
        set_current_trace(trace)
        assert get_current_trace() is not None
        clear_current_trace()
        assert get_current_trace() is None