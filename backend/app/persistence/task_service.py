"""
Persistent task service - adapter that syncs in-memory AppRuntime tasks with PostgreSQL.
Phase 4.18: PostgreSQL is source of truth; in-memory is runtime cache.
"""

from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PersistentTaskService:
    """
    Wraps in-memory task management with PostgreSQL persistence.

    Design:
    - PostgreSQL = source of truth for task records
    - In-memory AppRuntime = runtime cache for active tasks
    - Redis = distributed coordination state

    Graceful degradation: if DB is unavailable, falls back to in-memory only.
    """

    def __init__(self):
        self._db_available = True

    async def _try_db(self, operation, *args, **kwargs) -> Any:
        """Try a database operation; on failure, log and return None."""
        try:
            return await operation(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            logger.warning("Database operation failed", error=str(e)[:100])
            self._db_available = False
            return None

    async def create_task(
        self,
        task_id: str,
        task_text: str,
        tenant_id: str = "",
        user_id: str = "",
        max_iterations: int = 3,
    ) -> dict | None:
        """Persist a new task to PostgreSQL."""
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        return await self._try_db(
            repo.create_task,
            {
                "task_id": task_id, "task": task_text,
                "tenant_id": tenant_id, "user_id": user_id,
                "max_iterations": max_iterations, "status": "pending",
            },
        )

    async def update_status(self, task_id: str, status: str, error_message: str = "") -> dict | None:
        """Update task status in PostgreSQL."""
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        data = {"status": status, "updated_at": datetime.now(timezone.utc)}
        if error_message:
            data["error_message"] = error_message
        return await self._try_db(repo.update_task, task_id, data)

    async def save_result(self, task_id: str, result: dict) -> dict | None:
        """Save task execution result."""
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        return await self._try_db(
            repo.update_task, task_id,
            {"result": result, "status": result.get("status", "completed")},
        )

    async def get_task(self, task_id: str, tenant_id: str = "") -> dict | None:
        """Get task from PostgreSQL."""
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        task = await self._try_db(repo.get_task, task_id)
        if task and tenant_id and task.get("tenant_id") != tenant_id:
            return None
        return task

    async def list_tasks(
        self, tenant_id: str = "", limit: int = 100, offset: int = 0,
    ) -> list[dict]:
        """List tasks from PostgreSQL with tenant isolation."""
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        tasks = await self._try_db(repo.list_tasks, tenant_id=tenant_id)
        if tasks is None:
            return []
        return tasks[offset:offset + limit]

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task from PostgreSQL."""
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        result = await self._try_db(repo.delete_task, task_id)
        return result is True

    async def recover_tasks(self, tenant_id: str = "") -> list[dict]:
        """Recover all persisted tasks (for runtime recovery on restart)."""
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        tasks = await self._try_db(repo.list_tasks, tenant_id=tenant_id)
        return tasks or []

    async def get_task_count(self, tenant_id: str = "") -> int:
        """Get total task count."""
        tasks = await self.list_tasks(tenant_id=tenant_id, limit=10000)
        return len(tasks)

    @property
    def is_available(self) -> bool:
        return self._db_available