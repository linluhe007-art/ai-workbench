"""
TraceEvent — 追踪事件定义。

记录 Agent Runtime 中各组件的关键事件。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class TraceEvent:
    """
    追踪事件。

    字段：
    - trace_id: 追踪 ID（同一任务共享）
    - task_id: 任务 ID
    - component: 组件名称 (runtime/executor/loop/agent)
    - event_type: 事件类型 (start/end/error/metric/replan)
    - timestamp: 事件时间
    - duration_ms: 耗时（结束事件时填写）
    - metadata: 附加信息
    """
    trace_id: str
    task_id: str
    component: str
    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "component": self.component,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }