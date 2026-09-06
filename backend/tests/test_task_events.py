"""Phase 4.12 - TaskEvent system tests."""
import pytest
from app.execution.task_events import TaskEventStore, TaskEvent, TaskEventType


class TestTaskEventStore:
    def test_publish_creates_event(self):
        store = TaskEventStore()
        ev = store.publish("t1", TaskEventType.TASK_CREATED.value, "pending")
        assert ev.task_id == "t1"
        assert ev.event_type == "task_created"
        assert ev.sequence == 1

    def test_sequence_monotonic(self):
        store = TaskEventStore()
        e1 = store.publish("t1", "a", "x")
        e2 = store.publish("t1", "b", "x")
        e3 = store.publish("t1", "c", "x")
        assert e1.sequence == 1
        assert e2.sequence == 2
        assert e3.sequence == 3

    def test_different_tasks_independent_sequence(self):
        store = TaskEventStore()
        e1 = store.publish("t1", "a", "x")
        e2 = store.publish("t2", "a", "x")
        assert e1.sequence == 1
        assert e2.sequence == 1

    def test_get_events(self):
        store = TaskEventStore()
        store.publish("t1", "a", "x")
        store.publish("t1", "b", "x")
        events = store.get_events("t1")
        assert len(events) == 2

    def test_get_events_since_sequence(self):
        store = TaskEventStore()
        store.publish("t1", "a", "x")
        store.publish("t1", "b", "x")
        store.publish("t1", "c", "x")
        events = store.get_events("t1", since_sequence=2)
        assert len(events) == 1
        assert events[0].sequence == 3

    def test_get_events_empty(self):
        store = TaskEventStore()
        assert store.get_events("nonexistent") == []

    def test_get_last_sequence(self):
        store = TaskEventStore()
        assert store.get_last_sequence("t1") == 0
        store.publish("t1", "a", "x")
        store.publish("t1", "b", "x")
        assert store.get_last_sequence("t1") == 2

    def test_event_id_unique(self):
        store = TaskEventStore()
        e1 = store.publish("t1", "a", "x")
        e2 = store.publish("t1", "b", "x")
        assert e1.event_id != e2.event_id

    def test_clear_specific_task(self):
        store = TaskEventStore()
        store.publish("t1", "a", "x")
        store.publish("t2", "b", "x")
        store.clear("t1")
        assert store.get_events("t1") == []
        assert len(store.get_events("t2")) == 1

    def test_clear_all(self):
        store = TaskEventStore()
        store.publish("t1", "a", "x")
        store.publish("t2", "b", "x")
        store.clear()
        assert store.get_events("t1") == []
        assert store.get_events("t2") == []


class TestTaskEventModel:
    def test_to_dict(self):
        store = TaskEventStore()
        ev = store.publish("t1", TaskEventType.TASK_STARTED.value, "running", attempt=1, payload={"x": 1})
        d = ev.to_dict()
        assert d["task_id"] == "t1"
        assert d["event_type"] == "task_started"
        assert d["attempt"] == 1
        assert d["payload"]["x"] == 1
        assert "event_id" in d
        assert "timestamp" in d
        assert "sequence" in d

    def test_to_ws_event(self):
        store = TaskEventStore()
        ev = store.publish("t1", "task_cancelled", "cancelled")
        ws = ev.to_ws_event()
        assert ws["event"] == "task_cancelled"
        assert ws["task_id"] == "t1"
        assert "sequence" in ws["data"]


class TestTaskEventTypes:
    def test_all_types_defined(self):
        types = [e.value for e in TaskEventType]
        expected = [
            "task_created", "task_queued", "task_started", "task_paused",
            "task_resumed", "task_cancelled", "task_timeout", "task_retried",
            "task_completed", "task_failed", "task_evaluation_updated",
            "task_replanned", "task_artifact_created",
        ]
        for t in expected:
            assert t in types, f"Missing type: {t}"


class TestSubscribeNotify:
    @pytest.mark.asyncio
    async def test_subscribe_and_notify(self):
        store = TaskEventStore()
        received = []
        async def handler(ev):
            received.append(ev)
        store.subscribe("t1", handler)
        ev = store.publish("t1", "a", "x")
        await store.notify_subscribers(ev)
        assert len(received) == 1
        assert received[0].event_id == ev.event_id

    def test_unsubscribe(self):
        store = TaskEventStore()
        cb = lambda e: None
        store.subscribe("t1", cb)
        store.unsubscribe("t1", cb)
        assert store._subscribers.get("t1", []) == []