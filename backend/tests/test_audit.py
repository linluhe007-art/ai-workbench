"""
Phase 4.13 tests - Audit & Execution Explainability.
Covers: AuditRecord, AuditLogger CRUD, query filters, audit trail, agent audit,
API endpoints, AppRuntime integration, task lifecycle audit, pagination.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.audit.audit_log import AuditRecord, AuditLogger, get_audit_logger, reset_audit_logger
from app.runtime.manager import get_runtime, reset_runtime


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_audit_logger()
    yield
    reset_runtime()
    reset_audit_logger()


# =============================================================================
# AuditRecord Tests
# =============================================================================

class TestAuditRecord:
    def test_create_audit_record(self):
        record = AuditRecord(
            id="audit-1",
            timestamp=datetime.now(timezone.utc),
            actor="system",
            action="create_task",
            resource_type="task",
            resource_id="task-1",
            task_id="task-1",
        )
        assert record.id == "audit-1"
        assert record.actor == "system"
        assert record.action == "create_task"
        assert record.resource_type == "task"
        assert record.resource_id == "task-1"
        assert record.task_id == "task-1"

    def test_to_dict(self):
        ts = datetime.now(timezone.utc)
        record = AuditRecord(
            id="audit-1",
            timestamp=ts,
            actor="system",
            action="create_task",
            resource_type="task",
            resource_id="task-1",
            task_id="task-1",
            request_id="req-1",
            before={"status": "pending"},
            after={"status": "running"},
            metadata={"attempt": 1},
        )
        d = record.to_dict()
        assert d["id"] == "audit-1"
        assert d["actor"] == "system"
        assert d["action"] == "create_task"
        assert d["resource_type"] == "task"
        assert d["resource_id"] == "task-1"
        assert d["task_id"] == "task-1"
        assert d["request_id"] == "req-1"
        assert d["before"] == {"status": "pending"}
        assert d["after"] == {"status": "running"}
        assert d["metadata"] == {"attempt": 1}

    def test_to_dict_defaults(self):
        record = AuditRecord(
            id="audit-min",
            timestamp=datetime.now(timezone.utc),
            actor="agent",
            action="step_started",
            resource_type="execution",
            resource_id="exec-1",
        )
        d = record.to_dict()
        assert d["task_id"] is None
        assert d["request_id"] is None
        assert d["before"] == {}
        assert d["after"] == {}
        assert d["metadata"] == {}

    def test_to_dict_roundtrip(self):
        ts = datetime.now(timezone.utc)
        record = AuditRecord(
            id="r-1",
            timestamp=ts,
            actor="writer",
            action="artifact_created",
            resource_type="artifact",
            resource_id="art-1",
            task_id="task-1",
            request_id="req-1",
            before={},
            after={"name": "report.md"},
            metadata={"type": "markdown"},
        )
        d = record.to_dict()
        assert d["id"] == "r-1"
        assert d["actor"] == "writer"
        assert d["action"] == "artifact_created"
        assert d["after"]["name"] == "report.md"


# =============================================================================
# AuditLogger Tests
# =============================================================================

class TestAuditLogger:
    def test_record_returns_audit_record(self):
        logger = AuditLogger()
        record = logger.record("system", "create_task", "task", "task-1")
        assert isinstance(record, AuditRecord)
        assert record.actor == "system"
        assert record.action == "create_task"

    def test_multiple_records(self):
        logger = AuditLogger()
        for i in range(10):
            logger.record("system", f"action_{i}", "task", f"task-{i}")
        assert logger.count() == 10

    def test_query_by_task_id(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "task-1", task_id="task-1")
        logger.record("system", "task_started", "task", "task-1", task_id="task-1")
        logger.record("system", "create_task", "task", "task-2", task_id="task-2")

        records, total = logger.query(task_id="task-1")
        assert total == 2
        assert all(r.task_id == "task-1" for r in records)

    def test_query_by_actor(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "t1")
        logger.record("researcher", "step_started", "execution", "e1")
        logger.record("researcher", "step_completed", "execution", "e1")

        records, total = logger.query(actor="researcher")
        assert total == 2
        assert all(r.actor == "researcher" for r in records)

    def test_query_by_action(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "t1")
        logger.record("system", "task_completed", "task", "t1")
        logger.record("system", "create_task", "task", "t2")

        records, total = logger.query(action="create_task")
        assert total == 2
        assert all(r.action == "create_task" for r in records)

    def test_query_by_resource_type(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "t1")
        logger.record("agent", "artifact_created", "artifact", "a1")

        records, total = logger.query(resource_type="artifact")
        assert total == 1
        assert records[0].resource_type == "artifact"

    def test_query_by_resource_id(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "task-1")
        logger.record("system", "create_task", "task", "task-2")

        records, total = logger.query(resource_id="task-1")
        assert total == 1
        assert records[0].resource_id == "task-1"

    def test_query_by_request_id(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "t1", request_id="req-1")
        logger.record("system", "create_task", "task", "t2", request_id="req-2")

        records, total = logger.query(request_id="req-1")
        assert total == 1
        assert records[0].request_id == "req-1"

    def test_query_pagination_limit(self):
        logger = AuditLogger()
        for i in range(20):
            logger.record("system", f"action_{i}", "task", f"task-{i}")

        records, total = logger.query(limit=5)
        assert len(records) == 5
        assert total == 20

    def test_query_pagination_offset(self):
        logger = AuditLogger()
        for i in range(10):
            logger.record("system", f"action_{i}", "task", f"task-{i}")

        records, total = logger.query(limit=3, offset=3)
        assert len(records) == 3
        assert total == 10

    def test_query_combined_filters(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "t1", task_id="task-1")
        logger.record("researcher", "step_started", "execution", "e1", task_id="task-1")
        logger.record("system", "task_completed", "task", "t1", task_id="task-1")
        logger.record("system", "create_task", "task", "t2", task_id="task-2")

        records, total = logger.query(task_id="task-1", actor="system")
        assert total == 2
        assert all(r.task_id == "task-1" and r.actor == "system" for r in records)

    def test_query_no_results(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "t1")
        records, total = logger.query(task_id="nonexistent")
        assert total == 0
        assert records == []

    def test_get_audit_trail(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "t1", task_id="task-1")
        logger.record("system", "task_started", "task", "t1", task_id="task-1")
        logger.record("system", "task_completed", "task", "t1", task_id="task-1")

        trail = logger.get_audit_trail("task-1")
        assert len(trail) == 3
        # Verify chronological order
        for i in range(len(trail) - 1):
            assert trail[i].timestamp <= trail[i + 1].timestamp

    def test_get_audit_trail_empty(self):
        logger = AuditLogger()
        trail = logger.get_audit_trail("nonexistent")
        assert trail == []

    def test_get_agent_audit(self):
        logger = AuditLogger()
        logger.record("researcher", "step_started", "execution", "e1", task_id="t1")
        logger.record("analyst", "step_started", "execution", "e2", task_id="t1")
        logger.record("researcher", "step_completed", "execution", "e1", task_id="t1")

        records = logger.get_agent_audit("researcher")
        assert len(records) == 2
        assert all(r.actor == "researcher" for r in records)

    def test_get_agent_audit_empty(self):
        logger = AuditLogger()
        records = logger.get_agent_audit("nonexistent")
        assert records == []

    def test_get_resource_audit(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "task-1", task_id="t1")
        logger.record("system", "task_completed", "task", "task-1", task_id="t1")
        logger.record("system", "create_task", "task", "task-2", task_id="t2")

        records = logger.get_resource_audit("task", "task-1")
        assert len(records) == 2
        assert all(r.resource_id == "task-1" for r in records)

    def test_get_resource_audit_empty(self):
        logger = AuditLogger()
        records = logger.get_resource_audit("task", "nonexistent")
        assert records == []

    def test_clear_resets_all(self):
        logger = AuditLogger()
        logger.record("system", "create_task", "task", "t1")
        assert logger.count() == 1
        logger.clear()
        assert logger.count() == 0

    def test_max_records_eviction(self):
        logger = AuditLogger(max_records=5)
        for i in range(10):
            logger.record("system", f"action_{i}", "task", f"task-{i}")
        assert logger.count() == 5

    def test_count_after_records(self):
        logger = AuditLogger()
        assert logger.count() == 0
        logger.record("system", "a1", "task", "t1")
        logger.record("system", "a2", "task", "t2")
        assert logger.count() == 2

    def test_metadata_preserved(self):
        logger = AuditLogger()
        record = logger.record(
            "system", "task_completed", "task", "t1",
            metadata={"duration_ms": 500, "iterations": 3},
        )
        assert record.metadata["duration_ms"] == 500
        assert record.metadata["iterations"] == 3

    def test_before_after_preserved(self):
        logger = AuditLogger()
        record = logger.record(
            "system", "state_change", "task", "t1",
            before={"status": "running"},
            after={"status": "completed"},
        )
        assert record.before == {"status": "running"}
        assert record.after == {"status": "completed"}


# =============================================================================
# Global Singleton Tests
# =============================================================================

class TestAuditLoggerSingleton:
    def test_get_audit_logger_returns_singleton(self):
        reset_audit_logger()
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2

    def test_reset_creates_new_logger(self):
        reset_audit_logger()
        logger1 = get_audit_logger()
        reset_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is not logger2


# =============================================================================
# AppRuntime Integration Tests
# =============================================================================

class TestAppRuntimeAuditIntegration:
    def test_create_task_generates_audit(self):
        runtime = get_runtime()
        record = runtime.create_task("test task")
        assert runtime.audit_logger.count() >= 1
        records, total = runtime.audit_logger.query(task_id=record.task_id)
        assert total >= 1
        assert records[0].action == "create_task"

    @pytest.mark.asyncio
    async def test_cancel_task_generates_audit(self):
        runtime = get_runtime()
        record = runtime.create_task("test task")
        assert runtime.audit_logger.count() >= 1

        await runtime.cancel_task(record.task_id)
        records, _ = runtime.audit_logger.query(task_id=record.task_id, action="task_cancelled")
        assert len(records) >= 1

    def test_pause_task_generates_audit(self):
        runtime = get_runtime()
        record = runtime.create_task("test task")
        record.status = type(record.status)("RUNNING")

        async def _run():
            await runtime.pause_task(record.task_id)

        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(_run())
        except RuntimeError:
            asyncio.run(_run())

        records, _ = runtime.audit_logger.query(task_id=record.task_id, action="task_paused")
        assert len(records) >= 1

    def test_resume_task_generates_audit(self):
        runtime = get_runtime()
        record = runtime.create_task("test task")

        import asyncio
        async def _run():
            await runtime.resume_task(record.task_id)

        try:
            asyncio.get_event_loop().run_until_complete(_run())
        except RuntimeError:
            asyncio.run(_run())

        records, _ = runtime.audit_logger.query(task_id=record.task_id, action="task_resumed")
        assert len(records) >= 1

    def test_retry_task_generates_audit(self):
        runtime = get_runtime()
        record = runtime.create_task("test task")
        record.status = type(record.status)("FAILED")

        import asyncio
        async def _run():
            await runtime.retry_task(record.task_id)

        try:
            asyncio.get_event_loop().run_until_complete(_run())
        except RuntimeError:
            asyncio.run(_run())

        records, _ = runtime.audit_logger.query(task_id=record.task_id, action="task_retry")
        assert len(records) >= 1

    def test_multiple_tasks_audit_isolation(self):
        runtime = get_runtime()
        r1 = runtime.create_task("task one")
        r2 = runtime.create_task("task two")

        records1, _ = runtime.audit_logger.query(task_id=r1.task_id)
        records2, _ = runtime.audit_logger.query(task_id=r2.task_id)

        assert len(records1) >= 1
        assert len(records2) >= 1
        assert all(r.task_id == r1.task_id for r in records1)
        assert all(r.task_id == r2.task_id for r in records2)


# =============================================================================
# API Endpoint Tests
# =============================================================================

async def _get(path: str, params: dict | None = None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1{path}", params=params or {})
    return resp


async def _post(path: str, params: dict | None = None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1{path}", params=params or {})
    return resp


class TestAuditAPI:
    @pytest.mark.asyncio
    async def test_query_audit_empty(self):
        resp = await _get("/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_query_audit_after_create(self):
        runtime = get_runtime()
        runtime.create_task("test query audit")
        resp = await _get("/audit")
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_query_audit_by_task_id(self):
        runtime = get_runtime()
        record = runtime.create_task("specific task")
        resp = await _get("/audit", {"task_id": record.task_id})
        data = resp.json()
        assert data["total"] >= 1
        assert all(item["task_id"] == record.task_id for item in data["items"])

    @pytest.mark.asyncio
    async def test_query_audit_by_actor(self):
        runtime = get_runtime()
        runtime.create_task("actor test")
        resp = await _get("/audit", {"actor": "system"})
        data = resp.json()
        assert data["total"] >= 1
        assert all(item["actor"] == "system" for item in data["items"])

    @pytest.mark.asyncio
    async def test_query_audit_by_action(self):
        runtime = get_runtime()
        runtime.create_task("action test")
        resp = await _get("/audit", {"action": "create_task"})
        data = resp.json()
        assert data["total"] >= 1
        assert all(item["action"] == "create_task" for item in data["items"])

    @pytest.mark.asyncio
    async def test_query_audit_by_resource_type(self):
        runtime = get_runtime()
        runtime.create_task("resource test")
        resp = await _get("/audit", {"resource_type": "task"})
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_query_audit_pagination(self):
        runtime = get_runtime()
        for i in range(5):
            runtime.create_task(f"pagination test {i}")

        resp = await _get("/audit", {"limit": 2, "offset": 0})
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_query_audit_offset(self):
        runtime = get_runtime()
        for i in range(5):
            runtime.create_task(f"offset test {i}")

        resp = await _get("/audit", {"limit": 2, "offset": 2})
        data = resp.json()
        assert data["offset"] == 2

    @pytest.mark.asyncio
    async def test_task_audit_trail_exists(self):
        runtime = get_runtime()
        record = runtime.create_task("trail test")
        resp = await _get(f"/tasks/{record.task_id}/audit")
        data = resp.json()
        assert data["task_id"] == record.task_id
        assert data["exists"] is True
        assert data["total"] >= 1
        assert len(data["audit_trail"]) >= 1

    @pytest.mark.asyncio
    async def test_task_audit_trail_not_found(self):
        resp = await _get("/tasks/nonexistent-task/audit")
        data = resp.json()
        assert data["exists"] is False
        assert data["audit_trail"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_agent_audit(self):
        runtime = get_runtime()
        runtime.create_task("agent audit test")
        resp = await _get("/agents/default/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert "agent_id" in data
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_audit_stats(self):
        runtime = get_runtime()
        runtime.create_task("stats test")
        resp = await _get("/audit/stats")
        data = resp.json()
        assert data["total_records"] >= 1
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_record_audit_event(self):
        resp = await _post("/audit/record", {
            "actor": "test_agent",
            "action": "test_action",
            "resource_type": "test",
            "resource_id": "test-1",
        })
        data = resp.json()
        assert data["actor"] == "test_agent"
        assert data["action"] == "test_action"

    @pytest.mark.asyncio
    async def test_record_audit_with_task_id(self):
        resp = await _post("/audit/record", {
            "actor": "test_agent",
            "action": "test_action2",
            "resource_type": "test",
            "resource_id": "test-2",
            "task_id": "task-123",
            "request_id": "req-456",
        })
        data = resp.json()
        assert data["task_id"] == "task-123"
        assert data["request_id"] == "req-456"

    @pytest.mark.asyncio
    async def test_audit_api_response_schema(self):
        runtime = get_runtime()
        runtime.create_task("schema test")
        resp = await _get("/audit")
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "timestamp" in item
            assert "actor" in item
            assert "action" in item
            assert "resource_type" in item
            assert "resource_id" in item

    @pytest.mark.asyncio
    async def test_audit_task_not_found_returns_empty_trail(self):
        resp = await _get("/tasks/fake-task-id-12345/audit")
        data = resp.json()
        assert data["exists"] is False
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_query_audit_max_limit(self):
        resp = await _get("/audit", {"limit": 1000})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_query_audit_limit_zero_rejected(self):
        resp = await _get("/audit", {"limit": 0})
        assert resp.status_code == 422  # validation error

    @pytest.mark.asyncio
    async def test_query_audit_negative_offset_rejected(self):
        resp = await _get("/audit", {"offset": -1})
        assert resp.status_code == 422