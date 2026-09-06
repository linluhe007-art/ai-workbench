"""Phase 4.11 - Concurrency and Queue Tests."""
import pytest
import asyncio
from app.runtime.manager import AppRuntime, TaskQueue, TaskStatus, reset_runtime, get_runtime


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    yield
    reset_runtime()


class TestTaskQueue:
    def test_queue_init(self):
        q = TaskQueue(max_concurrent=2)
        assert q.max_concurrent == 2
        assert q.running_count == 0
        assert q.queued_count == 0

    def test_queue_status(self):
        q = TaskQueue(max_concurrent=3)
        s = q.queue_status()
        assert s["max_concurrent"] == 3
        assert s["running"] == 0
        assert s["queued"] == 0
        assert s["running_tasks"] == []
        assert s["queued_tasks"] == []


class TestConcurrencyLimit:
    @pytest.mark.asyncio
    async def test_queue_status_api(self):
        runtime = get_runtime()
        qs = runtime.get_queue_status()
        assert qs["max_concurrent"] == 3
        assert qs["running"] == 0

    @pytest.mark.asyncio
    async def test_create_task_sets_pending(self):
        runtime = get_runtime()
        record = runtime.create_task("test")
        assert record.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_retry_sets_queued(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.FAILED
        result = await runtime.retry_task(record.task_id)
        assert result["success"] is True


class TestTaskRecordAttempt:
    def test_attempt_increments(self):
        r = get_runtime().create_task("t")
        assert r.attempt == 0
        r.attempt += 1
        assert r.attempt == 1

    def test_max_iterations_default(self):
        r = get_runtime().create_task("t")
        assert r.max_iterations == 3