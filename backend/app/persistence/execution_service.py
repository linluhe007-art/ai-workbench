"""
Persistent execution service.
Phase 4.18: Persists execution history to PostgreSQL with graceful degradation.
"""

from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PersistentExecutionService:
    """Persists execution records to PostgreSQL."""

    def __init__(self):
        self._db_available = True

    async def _try_db(self, operation, *args, **kwargs) -> Any:
        try:
            return await operation(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            logger.warning("DB execution save failed", error=str(e)[:100])
            self._db_available = False
            return None

    async def save_execution(
        self,
        task_id: str,
        iteration: int,
        status: str,
        plan: dict | None = None,
        result: dict | None = None,
        feedback: dict | None = None,
        duration_ms: float = 0.0,
    ) -> dict | None:
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        return await self._try_db(repo.save_execution, {
            "task_id": task_id,
            "iteration": iteration,
            "status": status,
            "plan": plan,
            "result": result,
            "feedback": feedback,
            "duration_ms": duration_ms,
        })

    async def get_execution_history(self, task_id: str) -> list[dict]:
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        result = await self._try_db(repo.get_executions, task_id)
        return result or []

    async def get_success_rate(self, task_id: str) -> dict:
        history = await self.get_execution_history(task_id)
        total = len(history)
        if total == 0:
            return {"task_id": task_id, "total": 0, "success_rate": 0.0}
        succeeded = sum(1 for e in history if e.get("status") == "success")
        return {
            "task_id": task_id,
            "total": total,
            "success": succeeded,
            "failed": total - succeeded,
            "success_rate": succeeded / total,
        }

    async def get_metrics(self) -> dict:
        return {"db_available": self._db_available}

    @property
    def is_available(self) -> bool:
        return self._db_available