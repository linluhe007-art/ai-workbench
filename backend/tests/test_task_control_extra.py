"""Phase 4.11 - Additional State Transition and Integration Tests."""
import pytest
from app.runtime.manager import get_runtime, reset_runtime, TaskStatus, TaskRecord


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    yield
    reset_runtime()


class TestAllStatusValues:
    def test_all_statuses_in_enum(self):
        values = {s.value for s in TaskStatus}
        expected = {"pending", "running", "completed", "failed", "queued", "paused", "cancelled", "timeout"}
        assert values == expected

    def test_status_string_comparison(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.QUEUED == "queued"
        assert TaskStatus.PAUSED == "paused"
        assert TaskStatus.CANCELLED == "cancelled"
        assert TaskStatus.TIMEOUT == "timeout"


class TestRecordDefaults:
    def test_default_attempt(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.attempt == 0

    def test_default_max_iterations(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.max_iterations == 3

    def test_default_timeout(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.timeout_seconds is None

    def test_cancel_event_created(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.cancel_event is not None
        assert not r.cancel_event.is_set()

    def test_pause_event_created(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.pause_event is not None
        assert r.pause_event.is_set()  # not paused by default


class TestQueueStatusIntegration:
    @pytest.mark.asyncio
    async def test_queue_reflects_state(self):
        runtime = get_runtime()
        qs = runtime.get_queue_status()
        assert "max_concurrent" in qs
        assert "running" in qs
        assert "queued" in qs
        assert "running_tasks" in qs
        assert "queued_tasks" in qs

    @pytest.mark.asyncio
    async def test_create_multiple_tasks(self):
        runtime = get_runtime()
        r1 = runtime.create_task("t1")
        r2 = runtime.create_task("t2")
        tasks = runtime.list_tasks()
        assert len(tasks) == 2

    @pytest.mark.asyncio
    async def test_create_task_with_custom_max_iterations(self):
        runtime = get_runtime()
        record = runtime.create_task("t", max_iterations=5)
        assert record.max_iterations == 5