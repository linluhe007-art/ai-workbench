"""
PlanningMemoryContext — 规划阶段的记忆上下文。

从历史经验中提取的信息，用于增强 Planner 和 AgentSelector 的决策。
"""

from dataclasses import dataclass, field


@dataclass
class PlanningMemoryContext:
    """
    规划阶段的记忆上下文。

    字段：
    - similar_tasks: 相似任务的历史记录
    - recommended_agents: 推荐的 Agent 列表
    - historical_success_rate: 历史成功率 (0-1)
    - warnings: 历史教训/警告
    """
    similar_tasks: list[dict] = field(default_factory=list)
    recommended_agents: list[str] = field(default_factory=list)
    historical_success_rate: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "similar_tasks_count": len(self.similar_tasks),
            "recommended_agents": self.recommended_agents,
            "historical_success_rate": round(self.historical_success_rate, 3),
            "warnings": self.warnings,
        }

    @property
    def has_history(self) -> bool:
        """是否有历史经验"""
        return len(self.similar_tasks) > 0