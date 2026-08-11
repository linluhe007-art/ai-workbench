"""
AgentMemory — 单 Agent 经验记忆。

每个 Agent 拥有独立的事件记忆，
记录执行历史、学习经验和偏好。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryEvent:
    """单条记忆事件"""
    event_type: str
    content: Any
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentMemory:
    """
    单 Agent 的经验记忆。

    职责：
    - 记忆事件（remember）
    - 回忆事件（recall）
    - 按时间、类型、关键词检索

    每个 Agent 实例拥有独立的 AgentMemory。
    """

    def __init__(self, agent_id: str, max_events: int = 1000):
        self._agent_id = agent_id
        self._max_events = max_events
        self._events: list[MemoryEvent] = []

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def remember(
        self,
        event_type: str,
        content: Any,
        metadata: dict | None = None,
    ) -> MemoryEvent:
        """
        记忆一个事件。
        Args:
            event_type: 事件类型 (task_complete, error, learning, ...)
            content: 事件内容
            metadata: 附加元数据
        Returns:
            MemoryEvent
        """
        event = MemoryEvent(
            event_type=event_type,
            content=content,
            metadata=metadata or {},
        )
        self._events.append(event)

        # 超出上限时淘汰最旧的
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

        logger.debug("Agent remembered", agent=self._agent_id, type=event_type)
        return event

    def recall(
        self,
        query: str = "",
        event_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        回忆事件。
        Args:
            query: 关键词查询（匹配 content）
            event_type: 按事件类型过滤
            limit: 返回数量上限
        Returns:
            事件列表（最近的在前）
        """
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if query:
            query_lower = query.lower()
            events = [
                e for e in events
                if self._matches_query(e, query_lower)
            ]

        # 最近的在前
        events = list(reversed(events))

        return [
            {
                "event_type": e.event_type,
                "content": e.content,
                "metadata": e.metadata,
                "created_at": e.created_at.isoformat(),
            }
            for e in events[:limit]
        ]

    def get_recent(self, count: int = 10) -> list[dict]:
        """获取最近 N 条记忆"""
        events = self._events[-count:]
        events.reverse()
        return [
            {
                "event_type": e.event_type,
                "content": e.content,
                "metadata": e.metadata,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]

    def count_by_type(self, event_type: str) -> int:
        """统计指定类型的事件数量"""
        return sum(1 for e in self._events if e.event_type == event_type)

    @property
    def total_events(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()

    @staticmethod
    def _matches_query(event: MemoryEvent, query_lower: str) -> bool:
        """检查事件是否匹配查询"""
        # 匹配 content
        content_str = str(event.content).lower()
        if query_lower in content_str:
            return True
        # 匹配 metadata 值
        for v in event.metadata.values():
            if query_lower in str(v).lower():
                return True
        return False