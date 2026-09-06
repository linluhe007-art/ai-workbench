"""Trace Context Manager - Phase 5.11"""
from dataclasses import dataclass, field
from typing import Any
from contextlib import asynccontextmanager

from app.intelligence.trace.decision_store import get_trace_store


@dataclass
class TraceContext:
    """Context manager wrapper to auto-record decision traces."""

    task_id: str = ""
    user_id: str = ""
    traces: list[dict] = field(default_factory=list)

    def record(
        self,
        trace_type: str,
        component: str,
        input_data: dict,
        decision: dict,
        reason: str = "",
        confidence: float = 0.0,
        metadata: dict | None = None,
    ):
        store = get_trace_store()
        trace = store.add_trace(
            trace_type=trace_type,
            component=component,
            input_data=input_data,
            decision=decision,
            reason=reason,
            confidence=confidence,
            task_id=self.task_id,
            user_id=self.user_id,
            metadata=metadata,
        )
        self.traces.append(trace.to_dict())
        return trace

    def get_traces(self) -> list[dict]:
        return self.traces

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "traces": self.traces,
            "trace_count": len(self.traces),
        }


def create_trace_context(task_id: str = "", user_id: str = "") -> TraceContext:
    """Create a trace context for a specific task."""
    return TraceContext(task_id=task_id, user_id=user_id)
