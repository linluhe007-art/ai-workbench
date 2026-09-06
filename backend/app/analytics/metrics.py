"""Personal Metrics - Phase 5.7"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any


@dataclass
class PersonalMetrics:
    """Aggregated personal dashboard metrics."""

    # Today tasks
    tasks_today: int = 0
    tasks_completed_today: int = 0
    tasks_failed_today: int = 0
    tasks_running: int = 0

    # Efficiency
    average_duration_ms: float = 0.0
    success_rate: float = 0.0
    total_iterations: int = 0

    # Learning / Knowledge growth
    knowledge_items_added: int = 0
    experience_records_created: int = 0
    artifacts_generated: int = 0

    # Agent activity
    agents_active: int = 0
    agents_total: int = 0
    agent_executions_today: int = 0

    # Timestamp
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "tasks_today": self.tasks_today,
            "tasks_completed_today": self.tasks_completed_today,
            "tasks_failed_today": self.tasks_failed_today,
            "tasks_running": self.tasks_running,
            "efficiency": {
                "average_duration_ms": self.average_duration_ms,
                "success_rate": round(self.success_rate, 3),
                "total_iterations": self.total_iterations,
            },
            "knowledge_growth": {
                "knowledge_items_added": self.knowledge_items_added,
                "experience_records_created": self.experience_records_created,
                "artifacts_generated": self.artifacts_generated,
            },
            "agent_activity": {
                "agents_active": self.agents_active,
                "agents_total": self.agents_total,
                "agent_executions_today": self.agent_executions_today,
            },
            "generated_at": self.generated_at,
        }


class PersonalMetricsCollector:
    """Collects and aggregates personal dashboard metrics from various subsystems."""

    def __init__(self):
        self._task_store: Any = None
        self._experience_service: Any = None
        self._workspace_manager: Any = None
        self._agent_runtime: Any = None
        self._artifact_extractor: Any = None

    def set_task_store(self, store):
        self._task_store = store

    def set_experience_service(self, service):
        self._experience_service = service

    def set_workspace_manager(self, manager):
        self._workspace_manager = manager

    def set_agent_runtime(self, runtime):
        self._agent_runtime = runtime

    def set_artifact_extractor(self, extractor):
        self._artifact_extractor = extractor

    async def collect(self) -> PersonalMetrics:
        metrics = PersonalMetrics()
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Task metrics
        if self._task_store:
            try:
                all_tasks = await self._task_store.list_tasks() if hasattr(self._task_store, "list_tasks") else []
                if isinstance(all_tasks, list):
                    for t in all_tasks:
                        tid = t.get("task_id", "") or t.get("id", "")
                        created = t.get("created_at", "")
                        status = t.get("status", "")
                        if created:
                            try:
                                ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
                                if ct >= today:
                                    metrics.tasks_today += 1
                            except (ValueError, TypeError):
                                pass
                        if status == "completed":
                            metrics.tasks_completed_today += 1
                        elif status == "failed":
                            metrics.tasks_failed_today += 1
                        elif status == "running":
                            metrics.tasks_running += 1

                    total = len(all_tasks)
                    if total > 0:
                        metrics.success_rate = metrics.tasks_completed_today / max(total, 1)
            except Exception:
                pass

        # Agent activity
        if self._agent_runtime:
            try:
                agents = self._agent_runtime.list_running_agents() if hasattr(self._agent_runtime, "list_running_agents") else []
                metrics.agents_active = len(agents) if isinstance(agents, list) else 0
                all_agents = self._agent_runtime.list_agents() if hasattr(self._agent_runtime, "list_agents") else []
                metrics.agents_total = len(all_agents) if isinstance(all_agents, list) else 0
            except Exception:
                pass

        # Experience records
        if self._experience_service:
            try:
                exps = getattr(self._experience_service, "_records", None)
                if isinstance(exps, list):
                    metrics.experience_records_created = len(exps)
                elif hasattr(self._experience_service, "count"):
                    metrics.experience_records_created = await self._experience_service.count() if callable(getattr(self._experience_service, "count", None)) else 0
            except Exception:
                pass

        # Workspace artifacts
        if self._workspace_manager:
            try:
                wss = getattr(self._workspace_manager, "_workspaces", None)
                if isinstance(wss, dict):
                    count = 0
                    for ws in wss.values():
                        items = getattr(ws, "items", None) or getattr(ws, "_items", None) or []
                        count += len(items) if isinstance(items, list) else 0
                    metrics.artifacts_generated = count
            except Exception:
                pass

        return metrics


_collector: PersonalMetricsCollector | None = None


def get_personal_metrics_collector() -> PersonalMetricsCollector:
    global _collector
    if _collector is None:
        _collector = PersonalMetricsCollector()
    return _collector
