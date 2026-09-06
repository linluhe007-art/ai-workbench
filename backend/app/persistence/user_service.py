"""
Persistent user/role/tenant service.
Phase 4.18: Adapter that syncs AuthService with PostgreSQL.
"""

from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PersistentUserService:
    """Wraps AuthService user management with PostgreSQL persistence."""

    def __init__(self):
        self._db_available = True

    async def _try_db(self, operation, *args, **kwargs) -> Any:
        try:
            return await operation(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            logger.warning("DB user operation failed", error=str(e)[:100])
            self._db_available = False
            return None

    async def create_user(self, data: dict) -> dict | None:
        from app.database.repository import get_db_repo
        repo = get_db_repo()
        # Flatten metadata key
        db_data = {**data}
        if "metadata" in db_data:
            db_data["metadata_"] = db_data.pop("metadata")
        return await self._try_db(repo.create_user, db_data)

    async def get_user(self, user_id: str) -> dict | None:
        from app.database.repository import get_db_repo
        return await self._try_db(get_db_repo().get_user, user_id)

    async def list_users(self, tenant_id: str = "") -> list[dict]:
        from app.database.repository import get_db_repo
        result = await self._try_db(get_db_repo().list_users, tenant_id=tenant_id)
        return result or []

    async def update_user(self, user_id: str, data: dict) -> dict | None:
        from app.database.repository import get_db_repo
        return await self._try_db(get_db_repo().update_user, user_id, data)

    async def delete_user(self, user_id: str) -> bool:
        from app.database.repository import get_db_repo
        result = await self._try_db(get_db_repo().delete_user, user_id)
        return result is True

    async def create_role(self, data: dict) -> dict | None:
        from app.database.repository import get_db_repo
        return await self._try_db(get_db_repo().create_role, data)

    async def list_roles(self, tenant_id: str = "") -> list[dict]:
        from app.database.repository import get_db_repo
        result = await self._try_db(get_db_repo().list_roles, tenant_id=tenant_id)
        return result or []

    async def create_tenant(self, data: dict) -> dict | None:
        from app.database.repository import get_db_repo
        return await self._try_db(get_db_repo().create_tenant, data)

    async def list_tenants(self) -> list[dict]:
        from app.database.repository import get_db_repo
        result = await self._try_db(get_db_repo().list_tenants)
        return result or []

    @property
    def is_available(self) -> bool:
        return self._db_available