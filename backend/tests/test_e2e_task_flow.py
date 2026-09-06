"""Phase 4.20: E2E task flow tests."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from app.runtime.manager import AppRuntime, TaskRecord, TaskStatus, get_runtime, reset_runtime
from app.audit.audit_log import get_audit_logger, reset_audit_logger


@pytest.fixture(autouse=True)
def reset():
    reset_runtime()
    reset_audit_logger()
    yield
    reset_runtime()
    reset_audit_logger()


class TestFullTaskLifecycle:

    def test_create_task_creates_record_and_event(self):
        rt = AppRuntime()
        record = rt.create_task("test task")
        assert record.status == TaskStatus.PENDING
        events = rt.event_store.get_events(record.task_id)
        assert len(events) >= 1
        assert events[0].event_type == "task_created"

    def test_create_task_creates_audit(self):
        rt = AppRuntime()
        record = rt.create_task("audit test")
        audit = get_audit_logger()
        records, total = audit.query(task_id=record.task_id)
        assert total >= 1

    def test_task_record_to_dict_includes_all_fields(self):
        rt = AppRuntime()
        record = rt.create_task("complete test")
        d = record.to_dict()
        assert "task_id" in d
        assert "status" in d
        assert "created_at" in d
        assert "max_iterations" in d

    def test_cancel_transitions_correctly(self):
        rt = AppRuntime()
        record = rt.create_task("cancel me")
        record.status = TaskStatus.QUEUED
        assert record.can_transition("cancelled")

    def test_pause_resume_transitions(self):
        rt = AppRuntime()
        record = rt.create_task("pause test")
        record.status = TaskStatus.RUNNING
        assert record.can_transition("paused")
        record.status = TaskStatus.PAUSED
        assert record.can_transition("running")

    def test_completed_can_retry(self):
        rt = AppRuntime()
        record = rt.create_task("retry me")
        record.status = TaskStatus.COMPLETED
        assert record.can_transition("queued")

    def test_failed_can_retry(self):
        rt = AppRuntime()
        record = rt.create_task("retry fail")
        record.status = TaskStatus.FAILED
        assert record.can_transition("queued")


class TestTaskEventStoreE2E:

    def test_event_sequence_is_monotonic(self):
        rt = AppRuntime()
        record = rt.create_task("seq test")
        tid = record.task_id
        rt.event_store.publish(tid, "task_queued", "queued")
        rt.event_store.publish(tid, "task_started", "running")
        events = rt.event_store.get_events(tid)
        sequences = [e.sequence for e in events]
        assert sequences == sorted(sequences)

    def test_event_since_sequence_filter(self):
        rt = AppRuntime()
        record = rt.create_task("filter test")
        tid = record.task_id
        rt.event_store.publish(tid, "event_a", "state_a")
        rt.event_store.publish(tid, "event_b", "state_b")
        rt.event_store.publish(tid, "event_c", "state_c")
        seq1 = rt.event_store.get_events(tid)[0].sequence
        later = rt.event_store.get_events(tid, since_sequence=seq1)
        assert len(later) == 2

    def test_event_to_dict(self):
        rt = AppRuntime()
        record = rt.create_task("dict test")
        events = rt.event_store.get_events(record.task_id)
        d = events[0].to_dict()
        assert "event_id" in d
        assert "event_type" in d
        assert "sequence" in d


class TestAuditE2E:

    def test_audit_records_all_task_actions(self):
        rt = AppRuntime()
        record = rt.create_task("audit e2e")
        audit = get_audit_logger()
        audit.record("system", "task_started", "task", record.task_id, task_id=record.task_id)
        audit.record("system", "task_completed", "task", record.task_id, task_id=record.task_id)
        records, total = audit.query(task_id=record.task_id)
        assert total >= 3

    def test_audit_query_by_actor(self):
        audit = get_audit_logger()
        audit.record("agent-1", "step_completed", "execution", "exec-1", task_id="t1")
        audit.record("agent-2", "step_completed", "execution", "exec-2", task_id="t1")
        records, total = audit.query(actor="agent-1")
        assert total == 1

    def test_audit_query_by_action(self):
        audit = get_audit_logger()
        audit.record("sys", "task_created", "task", "t1")
        audit.record("sys", "task_cancelled", "task", "t1")
        records, total = audit.query(action="task_created")
        assert total == 1

    def test_audit_record_to_dict(self):
        audit = get_audit_logger()
        audit.record("sys", "test", "resource", "r1", task_id="t1", request_id="req1")
        records, _ = audit.query(task_id="t1")
        d = records[0].to_dict()
        assert d["actor"] == "sys"
        assert d["action"] == "test"
        assert d["task_id"] == "t1"


class TestArtifactFlow:

    def test_artifact_extraction_disabled_without_services(self):
        rt = AppRuntime()
        assert rt.artifact_extractor is not None
        assert rt.workspace is not None

    def test_workspace_creation(self):
        rt = AppRuntime()
        ws = rt.workspace.create_workspace("task-ws-1")
        assert ws is not None


class TestRequestIDFlow:

    def test_request_id_in_audit(self):
        audit = get_audit_logger()
        audit.record("sys", "test", "r", "r1", request_id="req-abc")
        records, _ = audit.query(request_id="req-abc")
        assert len(records) == 1

    def test_task_events_have_ids(self):
        rt = AppRuntime()
        record = rt.create_task("event id test")
        events = rt.event_store.get_events(record.task_id)
        assert all(e.event_id for e in events)
