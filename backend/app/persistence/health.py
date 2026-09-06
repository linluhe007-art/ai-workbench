"""
Persistence health checker - monitors database and Redis availability.
Phase 4.18: Reports healthy/degraded/unavailable status.
"""

from enum import Enum

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PersistenceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class PersistenceHealthChecker:
    """Monitors and reports persistence layer health."""

    def __init__(self):
        self._db_available = False
        self._redis_available = False

    async def check(self) -> PersistenceStatus:
        """Run health check and return overall status."""
        await self._check_db()
        await self._check_redis()

        if self._db_available and self._redis_available:
            return PersistenceStatus.HEALTHY
        elif self._db_available or self._redis_available:
            return PersistenceStatus.DEGRADED
        else:
            return PersistenceStatus.UNAVAILABLE

    async def _check_db(self) -> None:
        try:
            from app.database import check_db
            self._db_available = await check_db()
        except Exception:  # noqa: BLE001
            self._db_available = False

    async def _check_redis(self) -> None:
        try:
            from app.database.redis import check_redis
            self._redis_available = await check_redis()
        except Exception:  # noqa: BLE001
            self._redis_available = False

    @property
    def db_available(self) -> bool:
        return self._db_available

    @property
    def redis_available(self) -> bool:
        return self._redis_available

    def to_dict(self) -> dict:
        return {
            "database": "healthy" if self._db_available else "unavailable",
            "redis": "healthy" if self._redis_available else "unavailable",
            "overall": (
                "healthy" if self._db_available and self._redis_available
                else "degraded" if self._db_available or self._redis_available
                else "unavailable"
            ),
        }


_health_checker: PersistenceHealthChecker | None = None


def get_health_checker() -> PersistenceHealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = PersistenceHealthChecker()
    return _health_checker


def reset_health_checker() -> None:
    global _health_checker
    _health_checker = None