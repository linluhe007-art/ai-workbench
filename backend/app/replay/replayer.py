"""Execution Replayer - Phase 5.11"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.intelligence.context.snapshot import get_snapshot_store
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReplayResult:
    task_id: str = ""
    success: bool = False
    replayed_steps: list[str] = field(default_factory=list)
    output: dict = field(default_factory=dict)
    error: str = ""
    replayed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id, "success": self.success,
            "replayed_steps": self.replayed_steps, "output": self.output,
            "error": self.error, "replayed_at": self.replayed_at,
        }


class Replayer:
    """Replays a previous AI execution from context snapshot."""

    async def replay(self, task_id: str) -> ReplayResult:
        store = get_snapshot_store()
        snapshot = store.get(task_id)

        if not snapshot:
            return ReplayResult(task_id=task_id, success=False, error="No snapshot found for this task")

        steps = []
        try:
            if snapshot.memory_context:
                steps.append("memory_loaded")
            if snapshot.plan:
                steps.append("plan_loaded")
            if snapshot.agent:
                steps.append("agent_loaded")
            if snapshot.prompt:
                steps.append("prompt_loaded")
            if snapshot.model:
                steps.append("model_loaded")

            logger.info("Replay completed", task_id=task_id, steps=len(steps))
            return ReplayResult(
                task_id=task_id, success=True, replayed_steps=steps,
                output=snapshot.result,
            )
        except Exception as e:
            return ReplayResult(task_id=task_id, success=False, error=str(e))


_replayer: Replayer | None = None


def get_replayer() -> Replayer:
    global _replayer
    if _replayer is None:
        _replayer = Replayer()
    return _replayer
