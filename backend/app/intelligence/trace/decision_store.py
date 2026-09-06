"""Decision Trace Store - Phase 5.11"""
from typing import Any
from app.intelligence.trace.decision_trace import DecisionTrace, TraceType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DecisionTraceStore:
    """In-memory store for AI decision traces with filtering."""

    def __init__(self):
        self._traces: list[DecisionTrace] = []

    def add(self, trace: DecisionTrace):
        self._traces.append(trace)
        logger.info("Trace recorded", id=trace.id, type=trace.trace_type, component=trace.component)

    def add_trace(
        self,
        trace_type: str,
        component: str,
        input_data: dict,
        decision: dict,
        reason: str = "",
        confidence: float = 0.0,
        task_id: str = "",
        user_id: str = "",
        metadata: dict | None = None,
    ) -> DecisionTrace:
        trace = DecisionTrace.create(
            trace_type=trace_type,
            component=component,
            input_data=input_data,
            decision=decision,
            reason=reason,
            confidence=confidence,
            task_id=task_id,
            user_id=user_id,
            metadata=metadata,
        )
        self.add(trace)
        return trace

    def query(
        self,
        task_id: str | None = None,
        user_id: str | None = None,
        component: str | None = None,
        trace_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        results = self._traces

        if task_id:
            results = [t for t in results if t.task_id == task_id]
        if user_id:
            results = [t for t in results if t.user_id == user_id]
        if component:
            results = [t for t in results if t.component == component]
        if trace_type:
            results = [t for t in results if t.trace_type == trace_type]

        results.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in results[offset:offset + limit]]

    def get_by_task(self, task_id: str) -> list[dict]:
        return self.query(task_id=task_id, limit=500)

    def get_all(self) -> list[dict]:
        return self.query(limit=1000)

    def clear(self):
        self._traces.clear()


_store: DecisionTraceStore | None = None


def get_trace_store() -> DecisionTraceStore:
    global _store
    if _store is None:
        _store = DecisionTraceStore()
    return _store
