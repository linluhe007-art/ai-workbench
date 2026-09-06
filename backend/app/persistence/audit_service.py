"""Persistent audit service adapter. Phase 4.18."""
from typing import Any
from app.utils.logger import get_logger; logger = get_logger(__name__)

class PersistentAuditService:
    def __init__(self): self._db_available = True
    async def _try_db(self, o, *a, **kw):
        try: return await o(*a, **kw)
        except Exception as e: logger.warning("DB audit op failed", error=str(e)[:100]); self._db_available = False; return None
    async def record_audit(self, data): from app.database.repository import get_db_repo; return await self._try_db(get_db_repo().record_audit, data)
    async def query_audit(self, **filters): from app.database.repository import get_db_repo; r = await self._try_db(get_db_repo().query_audit, **filters); return r or ([], 0)
    @property
    def is_available(self): return self._db_available