"""Personal AI Orchestrator - Phase 5.10"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.os.context import UnifiedContext, ContextBuilder, get_context_builder
from app.os.decision import Decision, DecisionEngine, get_decision_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrchestrationStep:
    """A single step in the orchestration pipeline."""
    name: str
    status: str = "pending"  # pending, running, completed, failed
    result: dict = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class OrchestrationResult:
    """Complete result of the orchestration pipeline."""
    id: str = ""
    user_intent: str = ""
    success: bool = False
    context: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)
    steps: list[dict] = field(default_factory=list)
    task_id: str = ""
    recommendations: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_intent": self.user_intent,
            "success": self.success,
            "context": self.context,
            "decision": self.decision,
            "steps": self.steps,
            "task_id": self.task_id,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at,
        }


class PersonalAIOrchestrator:
    """Orchestrates the full AI OS pipeline: Intent -> Memory -> Plan -> Execute -> Learn."""

    def __init__(self):
        self._context_builder: ContextBuilder | None = None
        self._decision_engine: DecisionEngine | None = None
        self._task_store: Any = None
        self._agent_runtime: Any = None
        self._planner: Any = None
        self._improvement_engine: Any = None
        self._automation_scheduler: Any = None

    def set_context_builder(self, builder: ContextBuilder):
        self._context_builder = builder

    def set_decision_engine(self, engine: DecisionEngine):
        self._decision_engine = engine

    def set_task_store(self, store):
        self._task_store = store

    def set_agent_runtime(self, runtime):
        self._agent_runtime = runtime

    def set_planner(self, planner):
        self._planner = planner

    def set_improvement_engine(self, engine):
        self._improvement_engine = engine

    def set_automation_scheduler(self, scheduler):
        self._automation_scheduler = scheduler

    async def process(self, user_intent: str, task_category: str = "") -> OrchestrationResult:
        """Full orchestration pipeline."""
        import uuid
        import time

        result_id = str(uuid.uuid4())
        steps: list[OrchestrationStep] = []
        result = OrchestrationResult(id=result_id, user_intent=user_intent)

        ctx_builder = self._context_builder or get_context_builder()
        dec_engine = self._decision_engine or get_decision_engine()

        # Step 1: Memory Retrieval
        step1 = OrchestrationStep(name="memory_retrieval", status="running")
        t0 = time.time()
        try:
            context = await ctx_builder.build(user_intent=user_intent, task_category=task_category)
            step1.status = "completed"
            step1.result = {"memories_found": len(context.memory_snapshot.recent_experiences)}
        except Exception as e:
            step1.status = "failed"
            step1.error = str(e)
            context = UnifiedContext(user_intent=user_intent)
        step1.duration_ms = (time.time() - t0) * 1000
        steps.append(step1)

        # Step 2: Decision
        step2 = OrchestrationStep(name="decision", status="running")
        t0 = time.time()
        try:
            decision = dec_engine.decide(context)
            context.decision = decision.to_dict()
            step2.status = "completed"
            step2.result = {"action": decision.action, "confidence": decision.confidence}
        except Exception as e:
            step2.status = "failed"
            step2.error = str(e)
            decision = Decision(action="chat", confidence=0.3, reasoning="Fallback")
        step2.duration_ms = (time.time() - t0) * 1000
        steps.append(step2)

        # Step 3: Planning (if create_task)
        step3 = OrchestrationStep(name="planning", status="pending")
        task_id = ""
        if decision.action == "create_task" and self._task_store:
            step3.status = "running"
            t0 = time.time()
            try:
                task_desc = decision.task_description or user_intent
                if hasattr(self._task_store, "create_task"):
                    task = await self._task_store.create_task(task_desc)
                    task_id = task.get("task_id", task.get("id", ""))
                step3.status = "completed"
                step3.result = {"task_created": True, "task_id": task_id}
            except Exception as e:
                step3.status = "failed"
                step3.error = str(e)
            step3.duration_ms = (time.time() - t0) * 1000
        elif decision.action == "automate" and self._automation_scheduler:
            step3.status = "running"
            t0 = time.time()
            try:
                from app.automation.trigger import Trigger
                rule = self._automation_scheduler.add_rule(
                    name=f"Auto: {user_intent[:50]}",
                    trigger=Trigger.schedule("0 */4 * * *"),
                    action={"type": "create_task", "params": {"task": user_intent}},
                    description=user_intent,
                )
                step3.status = "completed"
                step3.result = {"automation_created": True, "rule_id": rule.id}
            except Exception as e:
                step3.status = "failed"
                step3.error = str(e)
            step3.duration_ms = (time.time() - t0) * 1000
        else:
            step3.status = "skipped"
        steps.append(step3)

        # Step 4: Agent Selection
        step4 = OrchestrationStep(name="agent_selection", status="pending")
        if decision.action == "create_task" and self._agent_runtime:
            step4.status = "running"
            t0 = time.time()
            try:
                if hasattr(self._agent_runtime, "list_agents"):
                    agents = self._agent_runtime.list_agents()
                    if agents:
                        step4.result = {"agents_considered": len(agents), "selected": agents[0].get("id", "")[:1]}
                step4.status = "completed"
            except Exception as e:
                step4.status = "failed"
                step4.error = str(e)
            step4.duration_ms = (time.time() - t0) * 1000
        else:
            step4.status = "skipped"
        steps.append(step4)

        # Step 5: Learning
        step5 = OrchestrationStep(name="learning", status="pending")
        if decision.should_learn and self._improvement_engine:
            step5.status = "running"
            t0 = time.time()
            try:
                if hasattr(self._improvement_engine, "analyze"):
                    await self._improvement_engine.analyze()
                step5.status = "completed"
                step5.result = {"learned": True}
            except Exception as e:
                step5.status = "failed"
                step5.error = str(e)
            step5.duration_ms = (time.time() - t0) * 1000
        else:
            step5.status = "skipped"
        steps.append(step5)

        # Finalize result
        result.success = all(s.status in ("completed", "skipped") for s in steps)
        result.context = context.to_dict()
        result.decision = decision.to_dict()
        result.steps = [s.to_dict() for s in steps]
        result.task_id = task_id

        # Recommendations
        recs = []
        if context.improvement_suggestions:
            recs.append("Review improvement suggestions")
        if decision.should_automate:
            recs.append("Consider setting up automation for this task")
        if not context.memory_snapshot.recent_experiences:
            recs.append("Build up memory by completing more tasks")
        result.recommendations = recs

        logger.info("Orchestration complete", id=result_id, success=result.success)
        return result


_orchestrator: PersonalAIOrchestrator | None = None


def get_orchestrator() -> PersonalAIOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PersonalAIOrchestrator()
    return _orchestrator
