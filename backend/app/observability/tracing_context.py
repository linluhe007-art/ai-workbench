"""
TraceContext - distributed tracing with span support.
Phase 4.21: Production tracing with trace_id, span_id, parent_span_id.
"""

import uuid
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Context variable for current trace
_current_trace: ContextVar = ContextVar("current_trace", default=None)


@dataclass
class Span:
    """A single span within a trace."""
    span_id: str
    trace_id: str
    parent_span_id: str = ""
    name: str = ""
    component: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    status: str = "ok"
    metadata: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "component": self.component,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "metadata": self.metadata,
            "events": self.events,
        }


@dataclass
class TraceContext:
    """
    Distributed tracing context.
    Manages trace_id and span hierarchy for a single request/task.
    """
    trace_id: str = ""
    spans: list[Span] = field(default_factory=list)
    _current_span_id: str = ""
    _start_time: float = 0.0

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = "trace-" + uuid.uuid4().hex[:12]
        self._start_time = time.monotonic()

    def start_span(self, name: str, component: str = "", metadata: dict | None = None) -> Span:
        span = Span(
            span_id="span-" + uuid.uuid4().hex[:8],
            trace_id=self.trace_id,
            parent_span_id=self._current_span_id,
            name=name,
            component=component,
            start_time=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        self._current_span_id = span.span_id
        self.spans.append(span)
        return span

    def end_span(self, span: Span, status: str = "ok") -> None:
        span.end_time = datetime.now(timezone.utc).isoformat()
        if span.start_time:
            try:
                start_dt = datetime.fromisoformat(span.start_time)
                span.duration_ms = (datetime.now(timezone.utc) - start_dt).total_seconds() * 1000
            except Exception:
                pass
        span.status = status
        self._current_span_id = span.parent_span_id

    def add_event(self, span: Span, event_name: str, data: dict | None = None) -> None:
        span.events.append({
            "name": event_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        })

    def get_root_span(self) -> Span | None:
        return self.spans[0] if self.spans else None

    def get_total_duration_ms(self) -> float:
        return (time.monotonic() - self._start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "spans": [s.to_dict() for s in self.spans],
            "total_duration_ms": self.get_total_duration_ms(),
            "span_count": len(self.spans),
        }


def get_current_trace() -> TraceContext | None:
    return _current_trace.get(None)


def set_current_trace(trace: TraceContext) -> None:
    _current_trace.set(trace)


def clear_current_trace() -> None:
    _current_trace.set(None)
