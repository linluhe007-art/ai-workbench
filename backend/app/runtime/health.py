"""
Runtime health status and degradation tracking.
Phase 4.19: Tracks PostgreSQL, Redis, and overall runtime health.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RuntimeHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ComponentHealth(str, Enum):
    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass
class RuntimeStatus:
    """Full runtime status snapshot."""
    instance_id: str = ""
    status: str = "starting"
    persistence_status: str = "unknown"
    redis_status: str = "unknown"
    started_at: str = ""
    uptime_seconds: float = 0.0
    active_tasks: int = 0
    components: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "status": self.status,
            "persistence_status": self.persistence_status,
            "redis_status": self.redis_status,
            "started_at": self.started_at,
            "uptime_seconds": self.uptime_seconds,
            "active_tasks": self.active_tasks,
            "components": self.components,
        }


class RuntimeHealthTracker:
    """Tracks runtime component health with degradation support."""

    def __init__(self, instance_id: str = ""):
        self._instance_id = instance_id
        self._started_at = datetime.now(timezone.utc)
        self._db_healthy = False
        self._redis_healthy = False
        self._overall = RuntimeHealth.UNKNOWN
        self._status = "starting"

    async def check_db(self) -> bool:
        """Check database connectivity."""
        try:
            from app.database import check_db
            self._db_healthy = await check_db()
        except Exception:
            self._db_healthy = False
        return self._db_healthy

    async def check_redis(self) -> bool:
        """Check Redis connectivity."""
        try:
            from app.database.redis import check_redis
            self._redis_healthy = await check_redis()
        except Exception:
            self._redis_healthy = False
        return self._redis_healthy

    async def check_all(self) -> RuntimeHealth:
        """Run all health checks and update status."""
        await self.check_db()
        await self.check_redis()

        if self._db_healthy and self._redis_healthy:
            self._overall = RuntimeHealth.HEALTHY
            self._status = "healthy"
        elif self._db_healthy or self._redis_healthy:
            self._overall = RuntimeHealth.DEGRADED
            self._status = "degraded"
        else:
            self._overall = RuntimeHealth.UNAVAILABLE
            self._status = "degraded"

        return self._overall

    def set_ready(self) -> None:
        """Mark runtime as ready after initialization."""
        self._status = "running"

    @property
    def overall(self) -> RuntimeHealth:
        return self._overall

    @property
    def is_db_healthy(self) -> bool:
        return self._db_healthy

    @property
    def is_redis_healthy(self) -> bool:
        return self._redis_healthy

    @property
    def status(self) -> str:
        return self._status

    def get_status(self) -> RuntimeStatus:
        """Get full runtime status."""
        now = datetime.now(timezone.utc)
        uptime = (now - self._started_at).total_seconds()
        return RuntimeStatus(
            instance_id=self._instance_id,
            status=self._status,
            persistence_status="healthy" if self._db_healthy else "unavailable",
            redis_status="healthy" if self._redis_healthy else "unavailable",
            started_at=self._started_at.isoformat(),
            uptime_seconds=uptime,
            components={
                "postgresql": "healthy" if self._db_healthy else "unavailable",
                "redis": "healthy" if self._redis_healthy else "unavailable",
            },
        )