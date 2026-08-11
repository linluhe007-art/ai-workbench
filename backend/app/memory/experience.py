"""
ExperienceMemory — 任务执行经验记忆。

记录每次任务执行的模式、使用的 Agent、结果和元数据。
支持按任务模式查询历史经验，为 Planner 和 AgentSelector 提供决策参考。
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExperienceRecord:
    """单条经验记录"""
    task_pattern: str
    agents: list[str]
    success: bool
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExperienceMemory:
    """
    任务执行经验记忆。

    职责：
    - 记录任务执行经验（pattern + agents + result）
    - 按任务模式查询历史经验
    - 支持关键词匹配和成功分数排序
    """

    def __init__(self):
        self._records: list[ExperienceRecord] = []

    def record_experience(
        self,
        task_pattern: str,
        agents: list[str],
        result: bool,
        metadata: dict | None = None,
    ) -> ExperienceRecord:
        """
        记录一次任务执行经验。
        Args:
            task_pattern: 任务模式/关键词
            agents: 使用的 Agent ID 列表
            result: 是否成功
            metadata: 附加元数据（如 duration_ms, step_count 等）
        Returns:
            ExperienceRecord
        """
        record = ExperienceRecord(
            task_pattern=task_pattern,
            agents=agents,
            success=result,
            duration_ms=metadata.get("duration_ms", 0) if metadata else 0,
            metadata=metadata or {},
        )
        self._records.append(record)
        logger.debug("Experience recorded", pattern=task_pattern, success=result)
        return record

    def query_experience(
        self,
        task_pattern: str,
        limit: int = 10,
    ) -> list[dict]:
        """
        按任务模式查询历史经验。
        支持关键词匹配，按匹配度 + 成功率排序。
        Args:
            task_pattern: 查询的任务模式
            limit: 返回数量上限
        Returns:
            经验记录列表（dict 格式）
        """
        if not task_pattern or not self._records:
            return []

        scored: list[tuple[float, ExperienceRecord]] = []
        query_lower = task_pattern.lower()

        for rec in self._records:
            score = self._compute_match_score(query_lower, rec.task_pattern.lower())
            if score > 0:
                # 加入成功分数权重
                if rec.success:
                    score += 0.5
                scored.append((score, rec))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, rec in scored[:limit]:
            results.append({
                "task_pattern": rec.task_pattern,
                "agents": rec.agents,
                "success": rec.success,
                "duration_ms": rec.duration_ms,
                "match_score": round(score, 3),
                "metadata": rec.metadata,
                "created_at": rec.created_at.isoformat(),
            })

        return results

    def get_success_rate(self, task_pattern: str) -> float:
        """获取指定任务模式的成功率"""
        matches = [r for r in self._records if task_pattern.lower() in r.task_pattern.lower()]
        if not matches:
            return 0.0
        return sum(1 for r in matches if r.success) / len(matches)

    def get_best_agents(self, task_pattern: str, limit: int = 3) -> list[str]:
        """获取指定任务模式下成功率最高的 Agent"""
        matches = [r for r in self._records if task_pattern.lower() in r.task_pattern.lower()]
        if not matches:
            return []

        agent_scores: dict[str, tuple[int, int]] = {}  # agent_id -> (success, total)
        for rec in matches:
            for agent_id in rec.agents:
                if agent_id not in agent_scores:
                    agent_scores[agent_id] = (0, 0)
                s, t = agent_scores[agent_id]
                agent_scores[agent_id] = (s + (1 if rec.success else 0), t + 1)

        ranked = sorted(
            agent_scores.items(),
            key=lambda x: x[1][0] / x[1][1] if x[1][1] > 0 else 0,
            reverse=True,
        )
        return [aid for aid, _ in ranked[:limit]]

    @property
    def total_records(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()

    @staticmethod
    def _compute_match_score(query: str, target: str) -> float:
        """简单的关键词匹配分数"""
        if query == target:
            return 1.0
        if query in target or target in query:
            return 0.8
        # 词级匹配
        query_words = set(query.split())
        target_words = set(target.split())
        if not query_words or not target_words:
            return 0.0
        overlap = query_words & target_words
        if overlap:
            return len(overlap) / max(len(query_words), len(target_words)) * 0.6
        return 0.0