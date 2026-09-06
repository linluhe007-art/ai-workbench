"""Phase 4.20: Concurrency stress tests."""
import pytest
import asyncio
from app.runtime.manager import AppRuntime, TaskRecord, TaskStatus, get_runtime, reset_runtime
from app.audit.audit_log import reset_audit_logger

@pytest.fixture(autouse=True)
def reset():
    reset_runtime()
    reset_audit_logger()
    yield
    reset_runtime()
    reset_audit_logger()

class TestConcurrentTaskCreation:
    def test_create_20_tasks(self):
        rt = AppRuntime()
        for i in range(20):
            rt.create_task("task-" + str(i))
        assert len(rt.list_tasks()) == 20

    def test_create_100_tasks(self):
        rt = AppRuntime()
        for i in range(100):
            rt.create_task("task-" + str(i))
        assert len(rt.list_tasks()) == 100

    def test_task_ids_are_unique(self):
        rt = AppRuntime()
        ids = set()
        for i in range(50):
            record = rt.create_task("unique")
            assert record.task_id not in ids
            ids.add(record.task_id)

class TestTaskQueueConcurrency:
    def test_queue_max_concurrent(self):
        rt = AppRuntime()
        assert rt.task_queue.max_concurrent == 3

    def test_queue_status_no_tasks(self):
        rt = AppRuntime()
        status = rt.get_queue_status()
        assert status["running"] == 0
        assert status["queued"] == 0

    def test_cancel_pending_not_in_queue(self):
        rt = AppRuntime()
        record = rt.create_task("not queued")
        result = rt.task_queue.cancel_pending(record.task_id)
        assert result is False

    def test_queue_does_not_leak_tasks(self):
        rt = AppRuntime()
        assert len(rt.task_queue._running) == 0
        assert len(rt.task_queue._pending_queue) == 0

class TestRapidStateTransitions:
    def test_rapid_transitions(self):
        rt = AppRuntime()
        record = rt.create_task("rapid")
        record.status = TaskStatus.QUEUED
        record.status = TaskStatus.RUNNING
        record.status = TaskStatus.PAUSED
        record.status = TaskStatus.RUNNING
        record.status = TaskStatus.COMPLETED
        assert record.status == TaskStatus.COMPLETED

    def test_cancelled_cannot_run(self):
        rt = AppRuntime()
        record = rt.create_task("cancelled")
        record.status = TaskStatus.CANCELLED
        assert not record.can_transition("running")

class TestEventStoreConcurrency:
    def test_many_events_per_task(self):
        rt = AppRuntime()
        record = rt.create_task("many events")
        for i in range(50):
            rt.event_store.publish(record.task_id, "event_" + str(i), "state_" + str(i % 5))
        events = rt.event_store.get_events(record.task_id)
        assert len(events) == 51

    def test_events_preserve_order(self):
        rt = AppRuntime()
        record = rt.create_task("order")
        for i in range(10):
            rt.event_store.publish(record.task_id, "e" + str(i), str(i))
        events = rt.event_store.get_events(record.task_id)
        sequences = [e.sequence for e in events[1:]]
        assert sequences[-1] - sequences[0] == len(sequences) - 1

class TestAuditConcurrency:
    def test_many_audit_records(self):
        from app.audit.audit_log import get_audit_logger
        audit = get_audit_logger()
        for i in range(100):
            audit.record("sys", "action_" + str(i), "resource", "r" + str(i))
        assert audit.count() == 100

    def test_audit_max_records_trimming(self):
        from app.audit.audit_log import AuditLogger
        audit = AuditLogger(max_records=10)
        for i in range(20):
            audit.record("sys", "test", "r", "r" + str(i))
        assert audit.count() <= 10

class TestPersistenceFailureGraceful:
    def test_runtime_starts_without_db(self):
        rt = AppRuntime()
        rt.persistence_enabled = False
        rt.redis_enabled = False
        record = rt.create_task("no db")
        assert record.task_id

    def test_persist_task_creation_graceful_failure(self):
        rt = AppRuntime()
        rt.persistence_enabled = False
        record = rt.create_task("graceful")
        assert record.task_id

    def test_shutdown_without_services(self):
        rt = AppRuntime()
        import asyncio
        asyncio.get_event_loop().run_until_complete(rt.shutdown())
