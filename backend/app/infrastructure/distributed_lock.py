"""
Distributed lock using Redis SET NX with TTL.
Phase 4.16: Enables cross-instance mutual exclusion for critical sections.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.infrastructure.redis_client import RedisClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DistributedLock:
    """
    Redis-based distributed lock with auto-expiry.

    Usage:
        lock = DistributedLock(redis, "my-lock")
        async with lock:
            # critical section
    """

    def __init__(self, redis_client: RedisClient, name: str, ttl_seconds: int = 30):
        self._redis = redis_client
        self._name = name
        self._key = f"lock:{name}"
        self._ttl = ttl_seconds
        self._token: str | None = None

    async def acquire(self, timeout: float = 10.0) -> bool:
        """
        Try to acquire the lock. Returns True if successful.

        If timeout > 0, retry until timeout.
        """
        self._token = str(uuid.uuid4())
        deadline = asyncio.get_event_loop().time() + timeout

        while True:
            acquired = await self._redis.setnx(self._key, self._token, self._ttl)
            if acquired:
                return True
            if timeout <= 0:
                return False
            if asyncio.get_event_loop().time() >= deadline:
                return False
            await asyncio.sleep(0.1)

    async def release(self) -> bool:
        """
        Release the lock using a Lua script to ensure atomicity
        (only release if the token matches).
        """
        if self._token is None:
            return False
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self._redis.client.eval(script, 1, self._key, self._token)
        released = result == 1
        if released:
            self._token = None
        return released

    async def extend(self, ttl_seconds: int | None = None) -> bool:
        """Extend the lock TTL. Only works if we still hold the lock."""
        if self._token is None:
            return False
        ttl = ttl_seconds or self._ttl
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = await self._redis.client.eval(script, 1, self._key, self._token, ttl)
        return result == 1

    @property
    def is_locked(self) -> bool:
        return self._token is not None

    async def __aenter__(self) -> "DistributedLock":
        acquired = await self.acquire()
        if not acquired:
            raise TimeoutError(f"Failed to acquire lock: {self._name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.release()


class LockManager:
    """Factory for named distributed locks."""

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client
        self._locks: dict[str, DistributedLock] = {}

    def get_lock(self, name: str, ttl_seconds: int = 30) -> DistributedLock:
        """Get or create a named lock."""
        if name not in self._locks:
            self._locks[name] = DistributedLock(self._redis, name, ttl_seconds)
        return self._locks[name]

    @asynccontextmanager
    async def lock(self, name: str, ttl_seconds: int = 30, timeout: float = 10.0) -> AsyncIterator[DistributedLock]:
        """Context manager for named lock acquisition."""
        lock = self.get_lock(name, ttl_seconds)
        acquired = await lock.acquire(timeout=timeout)
        if not acquired:
            raise TimeoutError(f"Failed to acquire lock: {name}")
        try:
            yield lock
        finally:
            await lock.release()