"""Persistent workspace service adapter. Phase 4.18."""
from typing import Any
from app.utils.logger import get_logger
logger = get_logger(__name__)

class PersistentWorkspaceService:
    def __init__(self):
        self._db_available = True

    async def _try_db(self, op, *a, **kw):
        try: return await op(*a, **kw)
        except Exception as e:
            logger.warning("DB workspace op failed", error=str(e)[:100])
            self._db_available = False
            return None

    async def create_workspace(self, data): from app.database.repository import get_db_repo; return await self._try_db(get_db_repo().create_workspace, data)
    async def get_workspace(self, wid): from app.database.repository import get_db_repo; return await self._try_db(get_db_repo().get_workspace, wid)
    async def list_workspaces(self, tenant_id=""): from app.database.repository import get_db_repo; r = await self._try_db(get_db_repo().list_workspaces, tenant_id=tenant_id); return r or []
    @property
    def is_available(self): return self._db_available