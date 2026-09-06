"""Phase 4.11 - Timeout and Additional Control Tests."""
import pytest
from app.runtime.manager import get_runtime, reset_runtime, TaskStatus, TaskRecord


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    yield
    reset_runtime()


class TestTimeout:
    def test_default_no_timeout(self):
        r = TaskRecord(task_id="t1", task="x")
        assert r.timeout_seconds is None

    def test_custom_timeout(self):
        r = TaskRecord(task_id="t1", task="x", timeout_seconds=120)
        assert r.timeout_seconds == 120

    def test_timeout_in_dict(self):
        r = TaskRecord(task_id="t1", task="x", timeout_seconds=60)
        d = r.to_dict()
        assert d["timeout_seconds"] == 60


class TestControlLogic:
    @pytest.mark.asyncio
    async def test_cancel_pending_task(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        result = await runtime.cancel_task(record.task_id)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_pause_non_running(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        result = await runtime.pause_task(record.task_id)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_resume_non_paused(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        result = await runtime.resume_task(record.task_id)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_retry_completed(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.COMPLETED
        result = await runtime.retry_task(record.task_id)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.CANCELLED
        result = await runtime.cancel_task(record.task_id)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_pause_already_failed(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.FAILED
        result = await runtime.pause_task(record.task_id)
        assert result["success"] is False


class TestWsBroadcast:
    def test_set_ws_broadcast(self):
        runtime = get_runtime()
        called = []
        async def mock_broadcast(task_id, event):
            called.append((task_id, event))
        runtime.set_ws_broadcast(mock_broadcast)
        assert runtime._ws_broadcast is not None

    @pytest.mark.asyncio
    async def test_cancel_broadcasts(self):
        runtime = get_runtime()
        events = []
        async def mock_broadcast(task_id, event):
            events.append(event)
        runtime.set_ws_broadcast(mock_broadcast)
        record = runtime.create_task("t")
        record.status = TaskStatus.RUNNING
        await runtime.cancel_task(record.task_id)
        assert len(events) >= 1
        assert events[0]["event"] == "task_cancelled"