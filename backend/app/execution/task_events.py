"""
TaskEvent - unified task state event system.
Provides monotonic sequence per task, event persistence, and replay support.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskEventType(str, Enum):
    """All supported task event types."""
    TASK_CREATED = "task_created"
    TASK_QUEUED = "task_queued"
    TASK_STARTED = "task_started"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"
    TASK_CANCELLED = "task_cancelled"
    TASK_TIMEOUT = "task_timeout"
    TASK_RETRIED = "task_retried"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_EVALUATION_UPDATED = "task_evaluation_updated"
    TASK_REPLANNED = "task_replanned"
    TASK_ARTIFACT_CREATED = "task_artifact_created"


@dataclass
class TaskEvent:
    """A single task lifecycle event with monotonic sequence."""
    event_id: str
    task_id: str
    event_type: str
    status: str
    timestamp: datetime
    attempt: int
    sequence: int
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "attempt": self.attempt,
            "sequence": self.sequence,
            "payload": self.payload,
        }

    def to_ws_event(self) -> dict:
        """Convert to WebSocket event format (backward compatible)."""
        return {
            "event": self.event_type,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "data": {
                **self.payload,
                "sequence": self.sequence,
                "attempt": self.attempt,
                "event_id": self.event_id,
            },
        }


class TaskEventStore:
    """
    In-memory event store with per-task monotonic sequence.
    Supports subscribe/replay/query.
    """

    def __init__(self):
        self._events: dict[str, list[TaskEvent]] = {}  # task_id -> events
        self._sequences: dict[str, int] = {}  # task_id -> next sequence
        self._subscribers: dict[str, list] = {}  # task_id -> list[callback]

    def publish(
        self,
        task_id: str,
        event_type: str,
        status: str,
        attempt: int = 0,
        payload: dict | None = None,
    ) -> TaskEvent:
        """Publish a new event with auto-incremented sequence."""
        seq = self._sequences.get(task_id, 0) + 1
        self._sequences[task_id] = seq

        event = TaskEvent(
            event_id=str(uuid.uuid4()),
            task_id=task_id,
            event_type=event_type,
            status=status,
            timestamp=datetime.now(timezone.utc),
            attempt=attempt,
            sequence=seq,
            payload=payload or {},
        )

        if task_id not in self._events:
            self._events[task_id] = []
        self._events[task_id].append(event)

        return event

    def get_events(
        self,
        task_id: str,
        since_sequence: int = 0,
        limit: int = 100,
    ) -> list[TaskEvent]:
        """Get events for a task, optionally since a given sequence."""
        events = self._events.get(task_id, [])
        if since_sequence > 0:
            events = [e for e in events if e.sequence > since_sequence]
        return events[:limit]

    def get_last_sequence(self, task_id: str) -> int:
        """Get the last sequence number for a task."""
        return self._sequences.get(task_id, 0)

    def subscribe(self, task_id: str, callback) -> None:
        """Subscribe to future events for a task."""
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        self._subscribers[task_id].append(callback)

    def unsubscribe(self, task_id: str, callback) -> None:
        """Unsubscribe from events."""
        subs = self._subscribers.get(task_id, [])
        if callback in subs:
            subs.remove(callback)

    async def notify_subscribers(self, event: TaskEvent) -> None:
        """Notify all subscribers of a new event."""
        subs = self._subscribers.get(event.task_id, [])
        for cb in subs:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event)
                else:
                    cb(event)
            except Exception:  # noqa: BLE001
                pass

    def clear(self, task_id: str | None = None) -> None:
        """Clear events (for testing)."""
        if task_id:
            self._events.pop(task_id, None)
            self._sequences.pop(task_id, None)
            self._subscribers.pop(task_id, None)
        else:
            self._events.clear()
            self._sequences.clear()
            self._subscribers.clear()


# Need asyncio for notify_subscribers
import asyncio