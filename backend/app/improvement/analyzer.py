"""Performance Analyzer - Phase 5.8"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AnalysisReport:
    """Analysis of system performance across tasks, agents, and workflows."""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Task-level analysis
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    task_success_rate: float = 0.0
    average_task_duration_ms: float = 0.0

    # Agent-level analysis
    agent_performance: list[dict] = field(default_factory=list)
    best_agent: str = ""
    worst_agent: str = ""

    # Workflow-level analysis
    workflow_stats: dict = field(default_factory=dict)

    # Bottlenecks
    bottlenecks: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "task_analysis": {
                "total_tasks": self.total_tasks,
                "completed_tasks": self.completed_tasks,
                "failed_tasks": self.failed_tasks,
                "success_rate": round(self.task_success_rate, 3),
                "average_duration_ms": self.average_duration_ms,
            },
            "agent_performance": self.agent_performance,
            "best_agent": self.best_agent,
            "worst_agent": self.worst_agent,
            "workflow_stats": self.workflow_stats,
            "bottlenecks": self.bottlenecks,
        }


class PerformanceAnalyzer:
    """Analyzes system performance from historical data."""

    def __init__(self):
        self._task_store: Any = None
        self._agent_runtime: Any = None
        self._experience_service: Any = None

    def set_task_store(self, store):
        self._task_store = store

    def set_agent_runtime(self, runtime):
        self._agent_runtime = runtime

    def set_experience_service(self, service):
        self._experience_service = service

    async def analyze(self) -> AnalysisReport:
        report = AnalysisReport()

        # Analyze tasks
        if self._task_store:
            try:
                tasks = await self._task_store.list_tasks() if hasattr(self._task_store, "list_tasks") else []
                if isinstance(tasks, list):
                    report.total_tasks = len(tasks)
                    durations = []
                    for t in tasks:
                        status = t.get("status", "")
                        if status == "completed":
                            report.completed_tasks += 1
                        elif status == "failed":
                            report.failed_tasks += 1
                        dur = t.get("duration_ms") or t.get("duration", 0)
                        if dur:
                            durations.append(float(dur))
                    if report.total_tasks > 0:
                        report.task_success_rate = report.completed_tasks / report.total_tasks
                    if durations:
                        report.average_task_duration_ms = sum(durations) / len(durations)

                    # Bottleneck: high failure rate
                    if report.total_tasks >= 5 and report.task_success_rate < 0.5:
                        report.bottlenecks.append({
                            "type": "high_failure_rate",
                            "severity": "high",
                            "detail": f"Task success rate is {report.task_success_rate*100:.0f}%",
                            "suggestion": "Review failed tasks for common patterns",
                        })
                    # Bottleneck: slow execution
                    if report.average_task_duration_ms > 30000:
                        report.bottlenecks.append({
                            "type": "slow_execution",
                            "severity": "medium",
                            "detail": f"Average duration {report.average_task_duration_ms:.0f}ms",
                            "suggestion": "Consider optimizing agent execution or reducing task complexity",
                        })
            except Exception:
                pass

        # Analyze agents
        if self._agent_runtime:
            try:
                agents = self._agent_runtime.list_agents() if hasattr(self._agent_runtime, "list_agents") else []
                for a in (agents or []):
                    aid = a.get("id", a.get("agent_id", "unknown"))
                    execs = a.get("executions", a.get("total_executions", 0))
                    errs = a.get("errors", 0)
                    rate = 1.0 - (errs / max(execs, 1))
                    report.agent_performance.append({
                        "agent_id": aid,
                        "executions": execs,
                        "errors": errs,
                        "success_rate": round(rate, 3),
                    })
                if report.agent_performance:
                    best = max(report.agent_performance, key=lambda x: x["success_rate"])
                    worst = min(report.agent_performance, key=lambda x: x["success_rate"])
                    report.best_agent = best["agent_id"]
                    report.worst_agent = worst["agent_id"]
            except Exception:
                pass

        # Workflow stats
        report.workflow_stats = {
            "agents_analyzed": len(report.agent_performance),
            "tasks_analyzed": report.total_tasks,
        }

        return report


_analyzer: PerformanceAnalyzer | None = None


def get_performance_analyzer() -> PerformanceAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = PerformanceAnalyzer()
    return _analyzer
