"""
MemoryRetriever — 记忆检索引擎。

支持多种检索策略：
- keyword matching: 关键词匹配
- success score ranking: 成功率排序
- time decay: 时间衰减（越近越重要）
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    item: Any
    score: float
    source: str  # "experience" / "agent_memory" / "knowledge"


class MemoryRetriever:
    """
    记忆检索引擎。

    支持三种排序策略（可组合）：
    1. keyword_score: 关键词匹配度 (0-1)
    2. success_score: 历史成功率 (0-1)
    3. time_decay: 时间衰减系数 (0-1, 越近越高)

    最终分数 = keyword_score * w1 + success_score * w2 + time_decay * w3
    """

    def __init__(
        self,
        keyword_weight: float = 0.4,
        success_weight: float = 0.3,
        decay_weight: float = 0.3,
        decay_half_life_hours: float = 24.0,
    ):
        self._kw_weight = keyword_weight
        self._success_weight = success_weight
        self._decay_weight = decay_weight
        self._half_life = decay_half_life_hours * 3600  # 转换为秒

    def retrieve(
        self,
        query: str,
        items: list[dict],
        limit: int = 10,
    ) -> list[RetrievalResult]:
        """
        检索并排序。
        Args:
            query: 查询关键词
            items: 待检索条目列表，每个条目需包含：
                - text: 用于关键词匹配的文本
                - success: bool（可选，用于 success_score）
                - created_at: ISO 时间字符串（可选，用于 time_decay）
            limit: 返回数量上限
        Returns:
            RetrievalResult 列表（按分数降序）
        """
        if not query or not items:
            return []

        now = datetime.now(timezone.utc)
        query_lower = query.lower()
        scored: list[RetrievalResult] = []

        for item in items:
            text = str(item.get("text", "")).lower()
            kw_score = self._keyword_score(query_lower, text)
            success = self._success_score(item)
            decay = self._time_decay(item, now)

            final_score = (
                self._kw_weight * kw_score
                + self._success_weight * success
                + self._decay_weight * decay
            )

            if final_score > 0:
                scored.append(RetrievalResult(
                    item=item,
                    score=round(final_score, 4),
                    source=item.get("source", "unknown"),
                ))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    @staticmethod
    def _keyword_score(query: str, text: str) -> float:
        """关键词匹配分数"""
        if not text:
            return 0.0
        if query in text:
            return 1.0
        # 词级匹配
        query_words = set(query.split())
        text_words = set(text.split())
        if not query_words:
            return 0.0
        overlap = query_words & text_words
        if overlap:
            return len(overlap) / len(query_words)
        return 0.0

    @staticmethod
    def _success_score(item: dict) -> float:
        """成功率分数"""
        if "success" not in item:
            return 0.5  # 无数据时中性分
        return 1.0 if item["success"] else 0.0

    def _time_decay(self, item: dict, now: datetime) -> float:
        """时间衰减分数（指数衰减）"""
        created_str = item.get("created_at")
        if not created_str:
            return 0.5  # 无时间数据时中性分

        try:
            if isinstance(created_str, str):
                created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            else:
                created = created_str
            elapsed = (now - created).total_seconds()
            if elapsed < 0:
                return 1.0  # 未来时间（异常）给满分
            # 指数衰减: score = 0.5^(elapsed / half_life)
            return math.pow(0.5, elapsed / self._half_life)
        except (ValueError, TypeError):
            return 0.5

    def retrieve_from_experiences(
        self,
        query: str,
        records: list[dict],
        limit: int = 10,
    ) -> list[RetrievalResult]:
        """
        从 ExperienceMemory 记录中检索。
        自动映射 experience 字段到通用格式。
        """
        items = []
        for rec in records:
            items.append({
                "text": rec.get("task_pattern", ""),
                "success": rec.get("success", False),
                "created_at": rec.get("created_at"),
                "source": "experience",
                "agents": rec.get("agents", []),
                "metadata": rec.get("metadata", {}),
            })
        return self.retrieve(query, items, limit)

    def retrieve_from_agent_events(
        self,
        query: str,
        events: list[dict],
        limit: int = 10,
    ) -> list[RetrievalResult]:
        """
        从 AgentMemory 事件中检索。
        自动映射 event 字段到通用格式。
        """
        items = []
        for evt in events:
            content = evt.get("content", "")
            items.append({
                "text": str(content),
                "created_at": evt.get("created_at"),
                "source": "agent_memory",
                "event_type": evt.get("event_type"),
            })
        return self.retrieve(query, items, limit)