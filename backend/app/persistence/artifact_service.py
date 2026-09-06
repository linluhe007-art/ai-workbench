"""Persistent artifact service adapter. Phase 4.18."""
from typing import Any
from app.utils.logger import get_logger
logger = get_logger(__name__)

class PersistentArtifactService:
    def __init__(self):
        self._db_available = True

    async def _try_db(self, operation, *args, **kwargs) -> Any:
        try:
            return await operation(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            logger.warning("DB artifact operation failed", error=str(e)[:100])
            self._db_available = False
            return None

    async def create_artifact(self, data: dict) -> dict | None:
        from app.database.repository import get_db_repo
        return await self._try_db(get_db_repo().create_artifact, data)

    async def get_artifact(self, artifact_id: str) -> dict | None:
        from app.database.repository import get_db_repo
        return await self._try_db(get_db_repo().get_artifact, artifact_id)

    async def list_artifacts(self, task_id: str = "", workspace_id: str = "", limit: int = 50, offset: int = 0) -> list[dict]:
        from app.database.repository import get_db_repo
        result = await self._try_db(get_db_repo().list_artifacts, task_id=task_id, workspace_id=workspace_id, limit=limit, offset=offset)
        return result or []

    async def search_artifacts(self, query: str = "", **filters: Any) -> tuple[list[dict], int]:
        from app.database.repository import get_db_repo
        result = await self._try_db(get_db_repo().search_artifacts, query=query, **filters)
        return result or ([], 0)

    async def delete_artifact(self, artifact_id: str) -> bool:
        from app.database.repository import get_db_repo
        result = await self._try_db(get_db_repo().delete_artifact, artifact_id)
        return result is True

    @property
    def is_available(self) -> bool:
        return self._db_available