"""Phase 4.11 - Task State Machine and Lifecycle Tests."""
import pytest
from app.runtime.manager import TaskStatus, TaskRecord, _VALID_TRANSITIONS


class TestTaskStatusEnum:
    def test_pending_value(self):
        assert TaskStatus.PENDING.value == "pending"

    def test_running_value(self):
        assert TaskStatus.RUNNING.value == "running"

    def test_completed_value(self):
        assert TaskStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        assert TaskStatus.FAILED.value == "failed"

    def test_queued_value(self):
        assert TaskStatus.QUEUED.value == "queued"

    def test_paused_value(self):
        assert TaskStatus.PAUSED.value == "paused"

    def test_cancelled_value(self):
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_timeout_value(self):
        assert TaskStatus.TIMEOUT.value == "timeout"

    def test_backward_compatible(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"


class TestStateTransitions:
    def test_pending_to_queued(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.PENDING)
        assert r.can_transition("queued") is True

    def test_pending_to_running(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.PENDING)
        assert r.can_transition("running") is True

    def test_running_to_paused(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.RUNNING)
        assert r.can_transition("paused") is True

    def test_running_to_completed(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.RUNNING)
        assert r.can_transition("completed") is True

    def test_running_to_failed(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.RUNNING)
        assert r.can_transition("failed") is True

    def test_running_to_cancelled(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.RUNNING)
        assert r.can_transition("cancelled") is True

    def test_running_to_timeout(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.RUNNING)
        assert r.can_transition("timeout") is True

    def test_paused_to_running(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.PAUSED)
        assert r.can_transition("running") is True

    def test_paused_to_cancelled(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.PAUSED)
        assert r.can_transition("cancelled") is True

    def test_completed_to_queued(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.COMPLETED)
        assert r.can_transition("queued") is True

    def test_failed_to_queued(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.FAILED)
        assert r.can_transition("queued") is True

    def test_cancelled_to_queued(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.CANCELLED)
        assert r.can_transition("queued") is True

    def test_timeout_to_queued(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.TIMEOUT)
        assert r.can_transition("queued") is True

    # Invalid transitions
    def test_completed_cannot_pause(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.COMPLETED)
        assert r.can_transition("paused") is False

    def test_failed_cannot_resume(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.FAILED)
        assert r.can_transition("running") is False

    def test_cancelled_cannot_pause(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.CANCELLED)
        assert r.can_transition("paused") is False

    def test_queued_cannot_complete(self):
        r = TaskRecord(task_id="t1", task="x", status=TaskStatus.QUEUED)
        assert r.can_transition("completed") is False


class TestTaskRecord:
    def test_to_dict_has_new_fields(self):
        r = TaskRecord(task_id="t1", task="test", status=TaskStatus.PENDING)
        d = r.to_dict()
        assert "attempt" in d
        assert "max_iterations" in d
        assert "timeout_seconds" in d
        assert d["attempt"] == 0

    def test_to_dict_backward_compatible(self):
        r = TaskRecord(task_id="t1", task="test", status=TaskStatus.PENDING)
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["task"] == "test"
        assert d["status"] == "pending"

    def test_error_message_in_dict(self):
        r = TaskRecord(task_id="t1", task="test", error_message="oops")
        d = r.to_dict()
        assert d["error_message"] == "oops"

    def test_no_error_message_when_none(self):
        r = TaskRecord(task_id="t1", task="test")
        d = r.to_dict()
        assert "error_message" not in d