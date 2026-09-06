"""Unified Context - Phase 5.10"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MemorySnapshot:
    """Snapshot of relevant memories for the current task."""
    profile: dict = field(default_factory=dict)
    preferences: list[dict] = field(default_factory=list)
    recent_experiences: list[dict] = field(default_factory=list)
    relevant_knowledge: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "profile": self.profile,
            "preferences": self.preferences,
            "recent_experiences": self.recent_experiences,
            "relevant_knowledge": self.relevant_knowledge,
        }


@dataclass
class SystemState:
    """Current state of the AI OS system."""
    agents_available: int = 0
    agents_active: int = 0
    automations_running: int = 0
    tasks_queued: int = 0
    tasks_running: int = 0
    last_improvement_at: str = ""
    overall_health: str = "healthy"

    def to_dict(self) -> dict:
        return {
            "agents_available": self.agents_available,
            "agents_active": self.agents_active,
            "automations_running": self.automations_running,
            "tasks_queued": self.tasks_queued,
            "tasks_running": self.tasks_running,
            "last_improvement_at": self.last_improvement_at,
            "overall_health": self.overall_health,
        }


@dataclass
class UnifiedContext:
    """Unified context aggregating all subsystem information."""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # User intent
    user_intent: str = ""
    task_category: str = ""

    # Memory
    memory_snapshot: MemorySnapshot = field(default_factory=MemorySnapshot)

    # System state
    system_state: SystemState = field(default_factory=SystemState)

    # Planning
    suggested_plan: dict = field(default_factory=dict)
    recommended_agents: list[str] = field(default_factory=list)

    # Improvement suggestions
    improvement_suggestions: list[dict] = field(default_factory=list)

    # Decision
    decision: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "user_intent": self.user_intent,
            "task_category": self.task_category,
            "memory_snapshot": self.memory_snapshot.to_dict(),
            "system_state": self.system_state.to_dict(),
            "suggested_plan": self.suggested_plan,
            "recommended_agents": self.recommended_agents,
            "improvement_suggestions": self.improvement_suggestions,
            "decision": self.decision,
        }


class ContextBuilder:
    """Builds unified context from various subsystems."""

    def __init__(self):
        self._memory_service: Any = None
        self._agent_runtime: Any = None
        self._task_store: Any = None
        self._improvement_engine: Any = None
        self._planner: Any = None

    def set_memory_service(self, svc):
        self._memory_service = svc

    def set_agent_runtime(self, rt):
        self._agent_runtime = rt

    def set_task_store(self, store):
        self._task_store = store

    def set_improvement_engine(self, engine):
        self._improvement_engine = engine

    def set_planner(self, planner):
        self._planner = planner

    async def build(self, user_intent: str = "", task_category: str = "") -> UnifiedContext:
        ctx = UnifiedContext(user_intent=user_intent, task_category=task_category)

        # Build memory snapshot
        memory = MemorySnapshot()
        if self._memory_service:
            try:
                if hasattr(self._memory_service, "search_memory"):
                    mems = await self._memory_service.search_memory(user_intent) if user_intent else []
                    if isinstance(mems, list):
                        memory.recent_experiences = mems[:5]
            except Exception:
                pass
        ctx.memory_snapshot = memory

        # Build system state
        state = SystemState()
        if self._agent_runtime:
            try:
                agents = getattr(self._agent_runtime, "list_agents", lambda: [])()
                state.agents_available = len(agents) if isinstance(agents, list) else 0
                running = getattr(self._agent_runtime, "list_running_agents", lambda: [])()
                state.agents_active = len(running) if isinstance(running, list) else 0
            except Exception:
                pass
        if self._task_store:
            try:
                tasks = await self._task_store.list_tasks() if hasattr(self._task_store, "list_tasks") else []
                if isinstance(tasks, list):
                    state.tasks_running = sum(1 for t in tasks if t.get("status") == "running")
                    state.tasks_queued = sum(1 for t in tasks if t.get("status") in ("pending", "queued"))
            except Exception:
                pass
        ctx.system_state = state

        # Improvement suggestions
        if self._improvement_engine:
            try:
                report = await self._improvement_engine.analyze() if hasattr(self._improvement_engine, "analyze") else None
                if report and hasattr(report, "bottlenecks"):
                    ctx.improvement_suggestions = report.bottlenecks[:3]
            except Exception:
                pass

        return ctx


_builder: ContextBuilder | None = None


def get_context_builder() -> ContextBuilder:
    global _builder
    if _builder is None:
        _builder = ContextBuilder()
    return _builder
