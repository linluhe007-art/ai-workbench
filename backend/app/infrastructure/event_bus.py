"""
Distributed Event Bus using Redis pub/sub.
Phase 4.16: Enables cross-instance event propagation for task, agent, and system events.
"""

import asyncio
import json
from typing import Any, Callable

from app.infrastructure.redis_client import RedisClient
from app.utils.logger import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[dict], Any]


class DistributedEventBus:
    """
    Redis pub/sub based event bus for multi-instance communication.

    Channels:
    - workbench:task:{task_id} — task-scoped events
    - workbench:agent:{agent_id} — agent-scoped events
    - workbench:system — system broadcast events
    - workbench:instance:* — instance heartbeat/status
    """

    CHANNEL_PREFIX = "workbench"
    SYSTEM_CHANNEL = f"{CHANNEL_PREFIX}:system"

    def __init__(self, redis_client: RedisClient, instance_id: str = ""):
        self._redis = redis_client
        self._instance_id = instance_id or f"instance-{id(self):x}"
        self._handlers: dict[str, list[EventHandler]] = {}
        self._listener_task: asyncio.Task | None = None
        self._running = False

    def channel_for_task(self, task_id: str) -> str:
        return f"{self.CHANNEL_PREFIX}:task:{task_id}"

    def channel_for_agent(self, agent_id: str) -> str:
        return f"{self.CHANNEL_PREFIX}:agent:{agent_id}"

    def channel_for_instance(self, instance_id: str = "") -> str:
        return f"{self.CHANNEL_PREFIX}:instance:{instance_id or self._instance_id}"

    async def publish(self, channel: str, event_type: str, data: dict | None = None) -> int:
        """Publish an event to a channel."""
        message = json.dumps({
            "event_type": event_type,
            "source_instance": self._instance_id,
            "data": data or {},
        })
        return await self._redis.publish(channel, message)

    async def publish_task_event(self, task_id: str, event_type: str, data: dict | None = None) -> int:
        """Publish a task-scoped event."""
        return await self.publish(self.channel_for_task(task_id), event_type, data)

    async def publish_agent_event(self, agent_id: str, event_type: str, data: dict | None = None) -> int:
        """Publish an agent-scoped event."""
        return await self.publish(self.channel_for_agent(agent_id), event_type, data)

    async def publish_system_event(self, event_type: str, data: dict | None = None) -> int:
        """Publish a system-wide broadcast event."""
        return await self.publish(self.SYSTEM_CHANNEL, event_type, data)

    def subscribe(self, channel: str, handler: EventHandler) -> None:
        """Register a handler for a channel."""
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)

    def unsubscribe(self, channel: str, handler: EventHandler) -> None:
        """Remove a handler from a channel."""
        if channel in self._handlers:
            self._handlers[channel] = [h for h in self._handlers[channel] if h is not handler]

    async def _dispatch(self, channel: str, raw_message: str) -> None:
        """Dispatch an incoming message to registered handlers."""
        handlers = self._handlers.get(channel, [])
        if not handlers:
            return
        try:
            payload = json.loads(raw_message)
        except json.JSONDecodeError:
            payload = {"raw": raw_message}
        for handler in handlers:
            try:
                result = handler(payload)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:  # noqa: BLE001
                pass

    async def start_listener(self, *channels: str) -> None:
        """Start listening on given channels (blocking in background task)."""
        if self._running:
            return
        self._running = True
        self._listener_task = asyncio.create_task(self._listen(channels))

    async def stop_listener(self) -> None:
        """Stop the background listener."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

    async def _listen(self, channels: tuple[str, ...]) -> None:
        """Background task that listens on subscribed channels."""
        try:
            pubsub = self._redis.client.pubsub()
            await pubsub.subscribe(*channels)
            logger.info("EventBus listener started", channels=list(channels))
            while self._running:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    channel = message["channel"]
                    data = message["data"]
                    await self._dispatch(channel, data)
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("EventBus listener error")
        finally:
            try:
                await pubsub.unsubscribe(*channels)
            except Exception:  # noqa: BLE001
                pass