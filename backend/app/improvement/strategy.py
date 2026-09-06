"""Strategy Engine - Phase 5.8"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.improvement.analyzer import AnalysisReport


@dataclass
class StrategyRecommendation:
    """A single strategy recommendation."""
    id: str = ""
    category: str = ""  # agent_selection, workflow, retry, resource
    title: str = ""
    description: str = ""
    priority: int = 0  # 0=low, 1=medium, 2=high
    expected_impact: str = ""
    action: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "expected_impact": self.expected_impact,
            "action": self.action,
        }


@dataclass
class StrategyPlan:
    """A set of strategy recommendations derived from analysis."""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recommendations: list[StrategyRecommendation] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "recommendations": [r.to_dict() for r in self.recommendations],
            "summary": self.summary,
        }


class StrategyEngine:
    """Generates strategy recommendations from analysis reports."""

    _counter: int = 0

    def generate(self, report: AnalysisReport) -> StrategyPlan:
        plan = StrategyPlan()
        recs: list[StrategyRecommendation] = []

        # Agent selection: prefer best agent
        if report.best_agent:
            recs.append(StrategyRecommendation(
                id=self._next_id(),
                category="agent_selection",
                title="Prefer high-performing agent",
                description=f"Agent '{report.best_agent}' has the best success rate. Route similar tasks there.",
                priority=1,
                expected_impact="Higher task success rate",
                action={"type": "update_selector", "prefer_agent": report.best_agent},
            ))

        # Agent selection: avoid worst agent
        if report.worst_agent and report.worst_agent != report.best_agent:
            recs.append(StrategyRecommendation(
                id=self._next_id(),
                category="agent_selection",
                title="Deprioritize low-performing agent",
                description=f"Agent '{report.worst_agent}' has the lowest success rate. Reduce its workload.",
                priority=2,
                expected_impact="Fewer task failures",
                action={"type": "update_selector", "deprioritize_agent": report.worst_agent},
            ))

        # Retry strategy
        if report.task_success_rate < 0.7 and report.total_tasks >= 3:
            recs.append(StrategyRecommendation(
                id=self._next_id(),
                category="retry",
                title="Increase retry limit",
                description=f"Success rate is {report.task_success_rate*100:.0f}%. Consider increasing max retries.",
                priority=1,
                expected_impact="More tasks may succeed on retry",
                action={"type": "update_config", "key": "max_retries", "suggested_value": 3},
            ))

        # Workflow optimization
        if report.average_task_duration_ms > 10000:
            recs.append(StrategyRecommendation(
                id=self._next_id(),
                category="workflow",
                title="Enable parallel execution",
                description="Tasks are slow. Enable parallel step execution where dependencies allow.",
                priority=1,
                expected_impact="Reduced end-to-end task duration",
                action={"type": "update_config", "key": "parallel_execution", "suggested_value": True},
            ))

        # Bottleneck-driven recommendations
        for bn in report.bottlenecks:
            severity = bn.get("severity", "low")
            prio = 2 if severity == "high" else 1 if severity == "medium" else 0
            recs.append(StrategyRecommendation(
                id=self._next_id(),
                category="bottleneck",
                title=f"Fix: {bn.get('type', 'unknown')}",
                description=bn.get("suggestion", bn.get("detail", "")),
                priority=prio,
                expected_impact="Improved system performance",
                action={"type": "resolve_bottleneck", "bottleneck_type": bn.get("type", "")},
            ))

        plan.recommendations = sorted(recs, key=lambda r: r.priority, reverse=True)
        plan.summary = f"Generated {len(plan.recommendations)} recommendations based on {report.total_tasks} tasks."
        return plan

    def _next_id(self) -> str:
        StrategyEngine._counter += 1
        return f"rec-{StrategyEngine._counter}"


_engine: StrategyEngine | None = None


def get_strategy_engine() -> StrategyEngine:
    global _engine
    if _engine is None:
        _engine = StrategyEngine()
    return _engine
