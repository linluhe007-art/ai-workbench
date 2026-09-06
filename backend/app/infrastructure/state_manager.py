"""
Distributed state manager using Redis hashes and key-value storage.
Phase 4.16: Enables sharing task/agent/runtime state across instances.
"""

from typing import Any

from app.infrastructure.redis_client import RedisClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DistributedStateManager:
    """
    Redis-backed distributed state for:
    - Task state (status, attempt, metadata)
    - Agent state (status, last heartbeat, current task)
    - Instance registry (active instances, heartbeats)
    - System configuration
    """

    KEY_PREFIX = "workbench:state"

    def __init__(self, redis_client: RedisClient):
        self._redis = redis_client

    # ── Task State ─────────────────────────────────────────

    def _task_key(self, task_id: str) -> str:
        return f"{self.KEY_PREFIX}:task:{task_id}"

    async def save_task_state(self, task_id: str, state: dict) -> None:
        """Save full task state."""
        await self._redis.hset(self._task_key(task_id), {
            k: str(v) if not isinstance(v, str) else v
            for k, v in state.items()
        })

    async def get_task_state(self, task_id: str) -> dict:
        """Get full task state."""
        return await self._redis.hgetall(self._task_key(task_id))

    async def delete_task_state(self, task_id: str) -> None:
        """Remove task state."""
        await self._redis.delete(self._task_key(task_id))

    async def update_task_field(self, task_id: str, field: str, value: Any) -> None:
        """Update a single task state field."""
        val = str(value) if not isinstance(value, str) else value
        await self._redis.hset(self._task_key(task_id), {field: val})

    # ── Agent State ────────────────────────────────────────

    def _agent_key(self, agent_id: str) -> str:
        return f"{self.KEY_PREFIX}:agent:{agent_id}"

    async def save_agent_state(self, agent_id: str, state: dict) -> None:
        """Save agent state."""
        await self._redis.hset(self._agent_key(agent_id), {
            k: str(v) if not isinstance(v, str) else v
            for k, v in state.items()
        })

    async def get_agent_state(self, agent_id: str) -> dict:
        """Get agent state."""
        return await self._redis.hgetall(self._agent_key(agent_id))

    async def delete_agent_state(self, agent_id: str) -> None:
        """Remove agent state."""
        await self._redis.delete(self._agent_key(agent_id))

    # ── Instance Registry ──────────────────────────────────

    INSTANCE_KEY = f"{KEY_PREFIX}:instances"

    async def register_instance(self, instance_id: str, metadata: dict | None = None) -> None:
        """Register an active instance with heartbeat TTL."""
        await self._redis.hset(self.INSTANCE_KEY, {
            instance_id: str(metadata or {}),
        })

    async def heartbeat(self, instance_id: str, ttl: int = 30) -> None:
        """Update instance heartbeat."""
        await self._redis.set(f"{self.KEY_PREFIX}:heartbeat:{instance_id}", "alive", ttl=ttl)

    async def get_active_instances(self) -> list[str]:
        """Get list of active instance IDs."""
        pattern = f"{self.KEY_PREFIX}:heartbeat:*"
        keys = await self._redis.keys(pattern)
        return [k.split(":")[-1] for k in keys]

    async def deregister_instance(self, instance_id: str) -> None:
        """Remove an instance from the registry."""
        await self._redis.hdel(self.INSTANCE_KEY, instance_id)
        await self._redis.delete(f"{self.KEY_PREFIX}:heartbeat:{instance_id}")

    # ── Global State ───────────────────────────────────────

    async def set_global(self, key: str, value: Any, ttl: int = 0) -> None:
        """Set a global key-value."""
        await self._redis.set(f"{self.KEY_PREFIX}:global:{key}", value, ttl=ttl)

    async def get_global(self, key: str) -> Any:
        """Get a global key-value."""
        return await self._redis.get_json(f"{self.KEY_PREFIX}:global:{key}")

    async def delete_global(self, key: str) -> None:
        """Delete a global key-value."""
        await self._redis.delete(f"{self.KEY_PREFIX}:global:{key}")

    # ── Counter ────────────────────────────────────────────

    async def incr_counter(self, name: str) -> int:
        """Atomically increment a named counter."""
        return await self._redis.incr(f"{self.KEY_PREFIX}:counter:{name}")