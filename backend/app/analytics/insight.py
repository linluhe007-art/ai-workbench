"""AI Insight Generator - Phase 5.7"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.analytics.metrics import PersonalMetrics


@dataclass
class Insight:
    type: str  # tip, warning, achievement, suggestion
    title: str
    message: str
    priority: int = 0  # 0=low, 1=medium, 2=high
    action: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "action": self.action,
        }


class AIInsightGenerator:
    """Generates personalized insights based on metrics."""

    def generate(self, metrics: PersonalMetrics) -> list[Insight]:
        insights: list[Insight] = []

        # Achievement: high success rate
        if metrics.tasks_completed_today > 0 and metrics.success_rate >= 0.8:
            insights.append(Insight(
                type="achievement",
                title="高效完成率",
                message=f"今天任务完成率 {metrics.success_rate*100:.0f}%，表现优秀！",
                priority=1,
                action="view_tasks",
            ))

        # Warning: failed tasks
        if metrics.tasks_failed_today > 0:
            insights.append(Insight(
                type="warning",
                title="任务失败提醒",
                message=f"今天有 {metrics.tasks_failed_today} 个任务失败，建议检查错误日志。",
                priority=1 if metrics.tasks_failed_today >= 3 else 0,
                action="review_failures",
            ))

        # Tip: idle agents
        if metrics.agents_total > 0 and metrics.agents_active == 0:
            insights.append(Insight(
                type="tip",
                title="Agent 空闲",
                message=f"当前 {metrics.agents_total} 个 Agent 均处于空闲状态，可以布置新任务。",
                priority=1,
                action="create_task",
            ))

        # Suggestion: knowledge growth
        if metrics.knowledge_items_added == 0 and metrics.tasks_completed_today >= 3:
            insights.append(Insight(
                type="suggestion",
                title="建议添加知识",
                message="今天完成了多个任务，可以将有价值的产出保存到知识库。",
                priority=0,
                action="open_knowledge",
            ))

        # Achievement: agent activity
        if metrics.agent_executions_today >= 10:
            insights.append(Insight(
                type="achievement",
                title="Agent 活跃",
                message=f"今天 Agent 执行了 {metrics.agent_executions_today} 次，系统运转正常。",
                priority=0,
                action="",
            ))

        # Tip: first task of the day
        if metrics.tasks_today == 0:
            insights.append(Insight(
                type="tip",
                title="新的一天",
                message="今天还没有任务，输入你想做的事，我来帮你安排！",
                priority=2,
                action="open_command",
            ))

        return insights


_insight_generator: AIInsightGenerator | None = None


def get_insight_generator() -> AIInsightGenerator:
    global _insight_generator
    if _insight_generator is None:
        _insight_generator = AIInsightGenerator()
    return _insight_generator
