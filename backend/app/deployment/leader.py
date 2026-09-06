"""
LeaderElection - Redis-based leader election for multi-instance deployments.
Phase 4.25: Uses DistributedLock for mutual exclusion leader election.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LeaderInfo:
    """Current leader information."""
    instance_id: str
    elected_at: str = ""
    term: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "elected_at": self.elected_at,
            "term": self.term,
            "metadata": self.metadata,
        }


class LeaderElection:
    """
    Redis-based leader election.

    Strategy:
    - Uses Redis SET NX with TTL for lock-based election
    - Leader holds the lock, periodically refreshes TTL
    - If leader fails, lock expires and another instance can acquire

    Usage:
        election = LeaderElection(redis_client, instance_id)
        await election.campaign()
        if election.is_leader:
            # do leader-only work
    """

    LOCK_KEY = "cluster:leader:lock"
    LOCK_TTL = 15  # seconds - short TTL for fast failover

    def __init__(self, redis_client=None, instance_id: str = "", cluster_manager=None):
        self._redis = redis_client
        self.instance_id = instance_id
        self._cluster = cluster_manager
        self._is_leader = False
        self._term = 0
        self._elected_at: str = ""
        self._refresh_task: asyncio.Task | None = None
        self._lock_token: str = ""

    @property
    def is_leader(self) -> bool:
        return self._is_leader

    async def campaign(self) -> bool:
        """
        Try to become leader.

        Returns True if this instance is now the leader.
        """
        if not self._redis:
            self._is_leader = True
            logger.info("Single instance mode - self-appointed leader", instance_id=self.instance_id)
            return True

        try:
            import uuid
            self._lock_token = str(uuid.uuid4())
            acquired = await self._redis.client.set(
                self.LOCK_KEY,
                self.instance_id,
                nx=True,
                ex=self.LOCK_TTL,
            )
            if acquired:
                self._is_leader = True
                self._term += 1
                self._elected_at = datetime.now(timezone.utc).isoformat()
                logger.info("Leader elected", instance_id=self.instance_id, term=self._term)

                if self._cluster:
                    await self._cluster.set_leader(self.instance_id)

                self._start_refresh()
                return True
            else:
                self._is_leader = False
                return False
        except Exception as e:
            logger.warning("Leader election failed, assuming follower", error=str(e))
            self._is_leader = False
            return False

    async def step_down(self) -> None:
        """Voluntarily give up leadership."""
        if not self._is_leader:
            return

        self._stop_refresh()
        if self._redis:
            try:
                # Only release if we still hold the lock
                current = await self._redis.client.get(self.LOCK_KEY)
                if current == self.instance_id:
                    await self._redis.client.delete(self.LOCK_KEY)
                    if self._cluster:
                        await self._cluster.set_leader(None)
            except Exception:
                pass

        self._is_leader = False
        logger.info("Leader stepped down", instance_id=self.instance_id)

    async def refresh(self) -> bool:
        """Refresh leader lock TTL. Returns True if still leader."""
        if not self._is_leader or not self._redis:
            return self._is_leader

        try:
            current = await self._redis.client.get(self.LOCK_KEY)
            if current == self.instance_id:
                await self._redis.client.expire(self.LOCK_KEY, self.LOCK_TTL)
                return True
            else:
                self._is_leader = False
                logger.warning("Lost leadership", instance_id=self.instance_id)
                return False
        except Exception:
            return self._is_leader

    async def get_current_leader(self) -> str | None:
        """Get the current leader instance_id."""
        if not self._redis:
            return self.instance_id
        try:
            return await self._redis.client.get(self.LOCK_KEY)
        except Exception:
            return None

    def get_info(self) -> LeaderInfo:
        return LeaderInfo(
            instance_id=self.instance_id if self._is_leader else "",
            elected_at=self._elected_at,
            term=self._term,
        )

    # -- Internal --

    def _start_refresh(self) -> None:
        async def _refresh_loop():
            while self._is_leader:
                await asyncio.sleep(self.LOCK_TTL * 0.5)  # Refresh at half TTL
                await self.refresh()
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(_refresh_loop())

    def _stop_refresh(self) -> None:
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            self._refresh_task = None