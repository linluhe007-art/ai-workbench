"""
Event bridge - connects TaskEventStore to DistributedEventBus.
Phase 4.19: Enables cross-instance task event propagation via Redis.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BridgedEvent:
    """An event that has been bridged to Redis for cross-instance propagation."""
    event_id: str
    source_instance_id: str
    event_type: str
    task_id: str
    sequence: int
    timestamp: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "source_instance_id": self.source_instance_id,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BridgedEvent":
        return cls(
            event_id=d.get("event_id", ""),
            source_instance_id=d.get("source_instance_id", ""),
            event_type=d.get("event_type", ""),
            task_id=d.get("task_id", ""),
            sequence=d.get("sequence", 0),
            timestamp=d.get("timestamp", ""),
            data=d.get("data", {}),
        )


class EventBridge:
    """
    Bridges in-memory TaskEventStore events to DistributedEventBus.

    Key guarantees:
    - Local events are published to Redis for other instances
    - Remote events are dispatched to local WebSocket subscribers
    - Duplicate filtering via event_id
    - No infinite loops (source_instance_id check)
    """

    def __init__(self, instance_id: str = ""):
        self._instance_id = instance_id
        self._event_bus = None
        self._seen_events: set[str] = set()
        self._max_seen = 10000
        self._ws_callbacks: dict[str, list[Callable]] = {}
        self._listener_task: asyncio.Task | None = None
        self._running = False

    def set_event_bus(self, event_bus) -> None:
        """Inject the DistributedEventBus."""
        self._event_bus = event_bus

    async def bridge_local_event(
        self,
        event_type: str,
        task_id: str,
        sequence: int = 0,
        event_id: str = "",
        data: dict | None = None,
    ) -> None:
        """Publish a local event to Redis for other instances."""
        if not self._event_bus:
            return
        try:
            bridged = BridgedEvent(
                event_id=event_id,
                source_instance_id=self._instance_id,
                event_type=event_type,
                task_id=task_id,
                sequence=sequence,
                timestamp=datetime.now(timezone.utc).isoformat(),
                data=data or {},
            )
            await self._event_bus.publish(
                self._event_bus.channel_for_task(task_id),
                event_type,
                bridged.to_dict(),
            )
        except Exception:
            logger.warning("Failed to bridge event", task_id=task_id, event_type=event_type)

    def _is_duplicate(self, event_id: str) -> bool:
        if event_id in self._seen_events:
            return True
        self._seen_events.add(event_id)
        if len(self._seen_events) > self._max_seen:
            # Trim oldest entries
            self._seen_events = set(list(self._seen_events)[-self._max_seen // 2:])
        return False

    def _is_local(self, source_instance_id: str) -> bool:
        return source_instance_id == self._instance_id or not source_instance_id

    async def handle_remote_event(self, payload: dict) -> None:
        """Handle an event received from Redis (another instance)."""
        event_type = payload.get("event_type", "")
        data = payload.get("data", {})

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {"raw": data}

        source = data.get("source_instance_id", "")
        event_id = data.get("event_id", "")
        task_id = data.get("task_id", "")

        # Don't process own events or duplicates
        if self._is_local(source) or self._is_duplicate(event_id):
            return

        logger.debug("Received remote event", task_id=task_id, event_type=event_type, source=source)

        # Dispatch to WebSocket subscribers
        await self._dispatch_to_ws(task_id, event_type, data)

    async def _dispatch_to_ws(self, task_id: str, event_type: str, data: dict) -> None:
        """Dispatch a remote event to local WebSocket subscribers."""
        callbacks = self._ws_callbacks.get(task_id, [])
        if not callbacks:
            return
        ws_data = {
            "event": event_type,
            "task_id": task_id,
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "data": {
                "sequence": data.get("sequence", 0),
                "event_id": data.get("event_id", ""),
                "from_instance": data.get("source_instance_id", ""),
                **data.get("data", {}),
            },
        }
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(task_id, ws_data)
                else:
                    cb(task_id, ws_data)
            except Exception:
                pass

    def register_ws_callback(self, task_id: str, callback: Callable) -> None:
        """Register a WebSocket broadcast callback for a task."""
        if task_id not in self._ws_callbacks:
            self._ws_callbacks[task_id] = []
        self._ws_callbacks[task_id].append(callback)

    def unregister_ws_callback(self, task_id: str, callback: Callable) -> None:
        """Unregister a WebSocket callback."""
        callbacks = self._ws_callbacks.get(task_id, [])
        if callback in callbacks:
            callbacks.remove(callback)
        if not callbacks:
            self._ws_callbacks.pop(task_id, None)

    async def start_listener(self, event_bus) -> None:
        """Start listening for remote events on the system channel and all task channels."""
        if self._running or not event_bus:
            return
        self._running = True
        self._event_bus = event_bus

        # Subscribe to system channel for broadcasts
        event_bus.subscribe(event_bus.SYSTEM_CHANNEL, self.handle_remote_event)

        # Start the global listener
        await event_bus.start_listener(event_bus.SYSTEM_CHANNEL)

        logger.info("EventBridge listener started", instance_id=self._instance_id)

    async def stop_listener(self) -> None:
        """Stop the event bridge listener."""
        self._running = False
        if self._event_bus:
            await self._event_bus.stop_listener()

    async def subscribe_task(self, task_id: str) -> None:
        """Subscribe to remote events for a specific task."""
        if not self._event_bus:
            return
        channel = self._event_bus.channel_for_task(task_id)
        self._event_bus.subscribe(channel, self.handle_remote_event)

    async def unsubscribe_task(self, task_id: str) -> None:
        """Unsubscribe from a task's remote events."""
        if not self._event_bus:
            return
        channel = self._event_bus.channel_for_task(task_id)
        if channel in self._event_bus._handlers:
            self._event_bus._handlers.pop(channel, None)