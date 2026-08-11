"""
TraceCollector — 追踪事件收集器。

收集和查询 TraceEvent，提供按 task_id 的追踪查询。
"""

import uuid
from datetime import datetime, timezone

from app.observability.trace import TraceEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TraceCollector:
    """
    追踪事件收集器。

    职责：
    - 收集 TraceEvent
    - 提供 start/end/error 便捷方法
    - 按 task_id 查询追踪链
    - 按 component 过滤
    """

    def __init__(self):
        self._events: list[TraceEvent] = []

    def start(
        self,
        trace_id: str,
        task_id: str,
        component: str,
        metadata: dict | None = None,
    ) -> TraceEvent:
        """记录开始事件"""
        event = TraceEvent(
            trace_id=trace_id,
            task_id=task_id,
            component=component,
            event_type="start",
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def end(
        self,
        trace_id: str,
        task_id: str,
        component: str,
        duration_ms: int = 0,
        metadata: dict | None = None,
    ) -> TraceEvent:
        """记录结束事件"""
        event = TraceEvent(
            trace_id=trace_id,
            task_id=task_id,
            component=component,
            event_type="end",
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def error(
        self,
        trace_id: str,
        task_id: str,
        component: str,
        error: str = "",
        metadata: dict | None = None,
    ) -> TraceEvent:
        """记录错误事件"""
        event = TraceEvent(
            trace_id=trace_id,
            task_id=task_id,
            component=component,
            event_type="error",
            metadata={"error": error, **(metadata or {})},
        )
        self._events.append(event)
        return event

    def metric(
        self,
        trace_id: str,
        task_id: str,
        component: str,
        metric_name: str,
        metric_value: float,
    ) -> TraceEvent:
        """记录指标事件"""
        event = TraceEvent(
            trace_id=trace_id,
            task_id=task_id,
            component=component,
            event_type="metric",
            metadata={"metric_name": metric_name, "metric_value": metric_value},
        )
        self._events.append(event)
        return event

    def get_trace(self, task_id: str) -> list[dict]:
        """获取指定任务的完整追踪链"""
        events = [e for e in self._events if e.task_id == task_id]
        return [e.to_dict() for e in events]

    def get_by_component(self, component: str) -> list[dict]:
        """按组件过滤事件"""
        events = [e for e in self._events if e.component == component]
        return [e.to_dict() for e in events]

    def get_errors(self, task_id: str | None = None) -> list[dict]:
        """获取错误事件"""
        events = [e for e in self._events if e.event_type == "error"]
        if task_id:
            events = [e for e in events if e.task_id == task_id]
        return [e.to_dict() for e in events]

    @property
    def total_events(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()

    @staticmethod
    def generate_trace_id() -> str:
        return f"trace-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def generate_task_id() -> str:
        return f"task-{uuid.uuid4().hex[:8]}"