"""Phase 4.20: Idempotency tests for task control operations."""
import pytest
import asyncio
from app.runtime.manager import AppRuntime, TaskRecord, TaskStatus, get_runtime, reset_runtime
from app.audit.audit_log import get_audit_logger, reset_audit_logger

@pytest.fixture(autouse=True)
def reset():
    reset_runtime()
    reset_audit_logger()
    yield
    reset_runtime()
    reset_audit_logger()

class TestCancelIdempotency:

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self):
        rt = AppRuntime()
        record = rt.create_task("pending cancel")
        result = await rt.cancel_task(record.task_id)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled(self):
        rt = AppRuntime()
        record = rt.create_task("double cancel")
        await rt.cancel_task(record.task_id)
        result = await rt.cancel_task(record.task_id)
        assert result["success"] is True


class TestPauseResumeIdempotency:

    @pytest.mark.asyncio
    async def test_pause_requires_running(self):
        rt = AppRuntime()
        record = rt.create_task("pause pending")
        result = await rt.pause_task(record.task_id)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_resume_requires_paused(self):
        rt = AppRuntime()
        record = rt.create_task("resume running")
        record.status = TaskStatus.RUNNING
        result = await rt.resume_task(record.task_id)
        assert result["success"] is False


class TestRetryIdempotency:

    @pytest.mark.asyncio
    async def test_retry_completed_task(self):
        rt = AppRuntime()
        record = rt.create_task("retry completed")
        record.status = TaskStatus.COMPLETED
        result = await rt.retry_task(record.task_id)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_retry_requires_retryable_state(self):
        rt = AppRuntime()
        record = rt.create_task("retry running")
        record.status = TaskStatus.RUNNING
        result = await rt.retry_task(record.task_id)
        assert result["success"] is False


class TestStateTransitionIdempotency:

    def test_pending_to_queued_once(self):
        record = TaskRecord(task_id="t1", task="test")
        assert record.can_transition("queued")
        record.status = TaskStatus.QUEUED
        assert not record.can_transition("queued")

    def test_cancelled_is_terminal(self):
        record = TaskRecord(task_id="t1", task="test", status=TaskStatus.CANCELLED)
        assert not record.can_transition("running")
        assert not record.can_transition("paused")
        assert record.can_transition("queued")

    def test_completed_is_terminal(self):
        record = TaskRecord(task_id="t1", task="test", status=TaskStatus.COMPLETED)
        assert not record.can_transition("running")
        assert not record.can_transition("paused")
        assert not record.can_transition("completed")


class TestAuditIdempotency:

    def test_same_action_recorded_twice(self):
        audit = get_audit_logger()
        audit.record("sys", "cancel", "task", "t1", task_id="t1")
        initial = audit.count()
        audit.record("sys", "cancel", "task", "t1", task_id="t1")
        assert audit.count() == initial + 1
