"""
Async Redis client wrapper for distributed infrastructure.
Phase 4.16: Distributed Runtime & Event Infrastructure.
"""

import json
from typing import Any

import redis.asyncio as redis

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Wrapper around redis.asyncio.Redis with typed helpers."""

    def __init__(self, url: str = ""):
        settings = get_settings()
        self._url = url or settings.redis_url
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis (idempotent)."""
        if self._client is not None:
            return
        self._client = redis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._client.ping()
        logger.info("Redis connected", url=self._url)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            raise RuntimeError("RedisClient not connected. Call connect() first.")
        return self._client

    # ── Key-Value ──────────────────────────────────────────

    async def set(self, key: str, value: Any, ttl: int = 0) -> None:
        val = json.dumps(value) if not isinstance(value, str) else value
        if ttl > 0:
            await self.client.set(key, val, ex=ttl)
        else:
            await self.client.set(key, val)

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def get_json(self, key: str) -> Any:
        val = await self.client.get(key)
        if val is None:
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return await self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    async def keys(self, pattern: str) -> list[str]:
        return await self.client.keys(pattern)

    async def ttl(self, key: str) -> int:
        return await self.client.ttl(key)

    # ── Hash ───────────────────────────────────────────────

    async def hset(self, name: str, mapping: dict) -> int:
        return await self.client.hset(name, mapping=mapping)

    async def hget(self, name: str, key: str) -> str | None:
        return await self.client.hget(name, key)

    async def hgetall(self, name: str) -> dict:
        return await self.client.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        return await self.client.hdel(name, *keys)

    # ── Set ────────────────────────────────────────────────

    async def sadd(self, key: str, *values: str) -> int:
        return await self.client.sadd(key, *values)

    async def srem(self, key: str, *values: str) -> int:
        return await self.client.srem(key, *values)

    async def smembers(self, key: str) -> set:
        return await self.client.smembers(key)

    async def sismember(self, key: str, value: str) -> bool:
        return await self.client.sismember(key, value)

    # ── List ───────────────────────────────────────────────

    async def lpush(self, key: str, *values: str) -> int:
        return await self.client.lpush(key, *values)

    async def rpop(self, key: str) -> str | None:
        return await self.client.rpop(key)

    async def llen(self, key: str) -> int:
        return await self.client.llen(key)

    async def lrange(self, key: str, start: int, end: int) -> list:
        return await self.client.lrange(key, start, end)

    # ── Pub/Sub ────────────────────────────────────────────

    async def publish(self, channel: str, message: Any) -> int:
        data = json.dumps(message) if not isinstance(message, str) else message
        return await self.client.publish(channel, data)

    async def subscribe(self, channel: str):
        """Return an async pubsub object for the given channel."""
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    # ── Atomic ─────────────────────────────────────────────

    async def incr(self, key: str) -> int:
        return await self.client.incr(key)

    async def setnx(self, key: str, value: str, ttl: int = 0) -> bool:
        """SET NX (only if not exists). Returns True if set."""
        if ttl > 0:
            result = await self.client.set(key, value, nx=True, ex=ttl)
        else:
            result = await self.client.set(key, value, nx=True)
        return result is True

    # ── Health ─────────────────────────────────────────────

    async def ping(self) -> bool:
        try:
            await self.client.ping()
            return True
        except Exception:  # noqa: BLE001
            return False