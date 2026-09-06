"""Phase 4.19: Runtime persistence integration tests."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.runtime.manager import AppRuntime, TaskRecord, TaskStatus, get_runtime, reset_runtime


@pytest.fixture(autouse=True)
def reset():
    reset_runtime()
    yield
    reset_runtime()


class TestAppRuntimePersistenceSettings:

    def test_default_persistence_enabled(self):
        rt = AppRuntime()
        assert rt.persistence_enabled is True
        assert rt.redis_enabled is True

    def test_instance_id_generated(self):
        rt = AppRuntime()
        assert rt.instance_id
        assert rt.instance_id.startswith("instance-")

    def test_started_at_set(self):
        rt = AppRuntime()
        assert rt.started_at

    def test_lazy_init_services_none(self):
        rt = AppRuntime()
        assert rt._health_tracker is None
        assert rt._event_bridge is None
        assert rt._task_service is None
        assert rt._redis_client is None

    def test_shutdown_flag_default_false(self):
        rt = AppRuntime()
        assert rt._shutting_down is False


class TestTaskCreationWithPersistence:

    def test_create_task_basic(self):
        rt = AppRuntime()
        record = rt.create_task("test task")
        assert record.task_id
        assert record.task == "test task"
        assert record.status == TaskStatus.PENDING

    def test_create_task_stored(self):
        rt = AppRuntime()
        record = rt.create_task("test")
        found = rt.get_task(record.task_id)
        assert found is not None
        assert found.task == "test"

    def test_create_task_with_persistence_disabled(self):
        rt = AppRuntime()
        rt.persistence_enabled = False
        record = rt.create_task("test")
        assert record.task_id

    def test_create_task_publishes_event(self):
        rt = AppRuntime()
        record = rt.create_task("test")
        events = rt.event_store.get_events(record.task_id)
        assert len(events) == 1
        assert events[0].event_type == "task_created"

    def test_list_tasks(self):
        rt = AppRuntime()
        rt.create_task("t1")
        rt.create_task("t2")
        tasks = rt.list_tasks()
        assert len(tasks) == 2


class TestTaskStatusTransitions:

    def test_pending_to_queued(self):
        record = TaskRecord(task_id="t1", task="test")
        assert record.can_transition("queued")

    def test_queued_to_running(self):
        record = TaskRecord(task_id="t1", task="test", status=TaskStatus.QUEUED)
        assert record.can_transition("running")

    def test_running_to_paused(self):
        record = TaskRecord(task_id="t1", task="test", status=TaskStatus.RUNNING)
        assert record.can_transition("paused")

    def test_running_to_completed(self):
        record = TaskRecord(task_id="t1", task="test", status=TaskStatus.RUNNING)
        assert record.can_transition("completed")

    def test_completed_to_queued(self):
        record = TaskRecord(task_id="t1", task="test", status=TaskStatus.COMPLETED)
        assert record.can_transition("queued")

    def test_invalid_transition(self):
        record = TaskRecord(task_id="t1", task="test", status=TaskStatus.COMPLETED)
        assert not record.can_transition("running")

    def test_task_record_to_dict(self):
        record = TaskRecord(task_id="t1", task="test", status=TaskStatus.RUNNING)
        d = record.to_dict()
        assert d["task_id"] == "t1"
        assert d["status"] == "running"
        assert "created_at" in d


class TestTaskQueue:

    def test_queue_status_default(self):
        rt = AppRuntime()
        status = rt.get_queue_status()
        assert status["max_concurrent"] == 3
        assert status["running"] == 0
        assert status["queued"] == 0

    def test_cancel_pending_task(self):
        rt = AppRuntime()
        record = rt.create_task("test")
        cancelled = rt.task_queue.cancel_pending(record.task_id)
        assert cancelled is False  # not in queue yet


class TestAppRuntimeMethods:

    def test_get_agents(self):
        rt = AppRuntime()
        agents = rt.get_agents()
        assert len(agents) >= 3
        agent_names = [a["name"] if isinstance(a, dict) else a.name for a in agents]
        assert "mock" in agent_names

    def test_get_metrics(self):
        rt = AppRuntime()
        metrics = rt.get_metrics()
        assert isinstance(metrics, dict)

    def test_get_history_empty(self):
        rt = AppRuntime()
        history = rt.get_history("non-existent")
        assert history == []

    def test_get_task_events_empty(self):
        rt = AppRuntime()
        events = rt.get_task_events("non-existent")
        assert events == []

    def test_set_ws_broadcast(self):
        rt = AppRuntime()
        called = []
        async def mock_broadcast(task_id, event):
            called.append((task_id, event))
        rt.set_ws_broadcast(mock_broadcast)
        assert rt._ws_broadcast is not None


class TestAppRuntimeNewProperties:

    def test_health_tracker_property(self):
        rt = AppRuntime()
        assert rt.health_tracker is None

    def test_event_bridge_property(self):
        rt = AppRuntime()
        assert rt.event_bridge is None


class TestGetRuntimeSingleton:

    def test_get_runtime_returns_same_instance(self):
        reset_runtime()
        rt1 = get_runtime()
        rt2 = get_runtime()
        assert rt1 is rt2

    def test_reset_runtime_creates_new_instance(self):
        reset_runtime()
        rt1 = get_runtime()
        reset_runtime()
        rt2 = get_runtime()
        assert rt1 is not rt2
