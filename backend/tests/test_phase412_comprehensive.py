"""Phase 4.12 - Comprehensive lifecycle, concurrency, and integration tests."""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.runtime.manager import get_runtime, reset_runtime, TaskStatus, TaskRecord, TaskQueue
from app.execution.task_events import TaskEventStore, TaskEventType
from app.api.v1.websocket import reset_ws_manager, get_ws_manager, make_event
from app.api.errors import ErrorCode, error_response, task_not_found, invalid_state


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_ws_manager()
    yield
    reset_runtime()
    reset_ws_manager()


# --- Full Lifecycle ---

class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_create_to_complete(self):
        runtime = get_runtime()
        r = runtime.create_task("t")
        assert r.status == TaskStatus.PENDING
        events = runtime.get_task_events(r.task_id)
        assert any(e["event_type"] == "task_created" for e in events)

    @pytest.mark.asyncio
    async def test_create_cancel_flow(self):
        runtime = get_runtime()
        r = runtime.create_task("t")
        r.status = TaskStatus.RUNNING
        result = await runtime.cancel_task(r.task_id)
        assert result["success"] is True
        assert r.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_create_pause_resume_flow(self):
        runtime = get_runtime()
        r = runtime.create_task("t")
        r.status = TaskStatus.RUNNING
        p = await runtime.pause_task(r.task_id)
        assert p["success"] is True
        assert r.status == TaskStatus.PAUSED
        res = await runtime.resume_task(r.task_id)
        assert res["success"] is True
        assert r.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_fail_retry_flow(self):
        runtime = get_runtime()
        r = runtime.create_task("t")
        r.status = TaskStatus.FAILED
        result = await runtime.retry_task(r.task_id)
        assert result["success"] is True


# --- Idempotent Control ---

class TestIdempotentControl:
    @pytest.mark.asyncio
    async def test_double_cancel(self):
        runtime = get_runtime()
        r = runtime.create_task("t")
        r.status = TaskStatus.RUNNING
        r1 = await runtime.cancel_task(r.task_id)
        assert r1["success"] is True
        r2 = await runtime.cancel_task(r.task_id)
        assert r2["success"] is False

    @pytest.mark.asyncio
    async def test_double_pause(self):
        runtime = get_runtime()
        r = runtime.create_task("t")
        r.status = TaskStatus.RUNNING
        r1 = await runtime.pause_task(r.task_id)
        assert r1["success"] is True
        r2 = await runtime.pause_task(r.task_id)
        assert r2["success"] is False

    @pytest.mark.asyncio
    async def test_double_resume(self):
        runtime = get_runtime()
        r = runtime.create_task("t")
        r.status = TaskStatus.PAUSED
        r1 = await runtime.resume_task(r.task_id)
        assert r1["success"] is True
        r2 = await runtime.resume_task(r.task_id)
        assert r2["success"] is False


# --- Concurrent Control ---

class TestConcurrentControl:
    @pytest.mark.asyncio
    async def test_cancel_and_pause_race(self):
        runtime = get_runtime()
        r = runtime.create_task("t")
        r.status = TaskStatus.RUNNING
        results = await asyncio.gather(
            runtime.cancel_task(r.task_id),
            runtime.pause_task(r.task_id),
            return_exceptions=True,
        )
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        assert success_count == 1


# --- Queue ---

class TestTaskQueue:
    def test_queue_init(self):
        q = TaskQueue(max_concurrent=5)
        assert q.max_concurrent == 5
        assert q.running_count == 0
        assert q.queued_count == 0

    def test_queue_status_fields(self):
        q = TaskQueue()
        s = q.queue_status()
        assert "max_concurrent" in s
        assert "running" in s
        assert "queued" in s
        assert "running_tasks" in s
        assert "queued_tasks" in s

    @pytest.mark.asyncio
    async def test_runtime_queue_status(self):
        runtime = get_runtime()
        qs = runtime.get_queue_status()
        assert qs["max_concurrent"] == 3


# --- WebSocket ---

class TestWebSocket:
    def test_make_event(self):
        ev = make_event("task_started", "t1", {"attempt": 1})
        assert ev["event"] == "task_started"
        assert ev["task_id"] == "t1"
        assert "timestamp" in ev

    def test_ws_manager_init(self):
        m = get_ws_manager()
        assert m.total_connections == 0

    def test_ws_manager_subscriber_count(self):
        m = get_ws_manager()
        assert m.subscriber_count("t1") == 0


# --- Error Model ---

class TestErrorModel:
    def test_all_error_codes(self):
        codes = [
            ErrorCode.TASK_NOT_FOUND, ErrorCode.INVALID_TASK_STATE,
            ErrorCode.TASK_ALREADY_COMPLETED, ErrorCode.TASK_ALREADY_RUNNING,
            ErrorCode.TASK_ALREADY_CANCELLED, ErrorCode.TASK_TIMEOUT,
            ErrorCode.TASK_CONTROL_CONFLICT, ErrorCode.QUEUE_FULL,
            ErrorCode.TASK_RETRY_EXHAUSTED, ErrorCode.INVALID_REQUEST,
            ErrorCode.INTERNAL_ERROR, ErrorCode.ARTIFACT_NOT_FOUND,
            ErrorCode.WORKSPACE_NOT_FOUND,
        ]
        assert len(codes) == 13
        assert len(set(codes)) == 13

    def test_error_response_structure(self):
        resp = error_response("TEST", "msg", {"x": 1})
        assert resp.status_code == 400

    def test_task_not_found_response(self):
        resp = task_not_found("t1")
        assert resp.status_code == 404

    def test_invalid_state_response(self):
        resp = invalid_state("completed", "pause")
        assert resp.status_code == 409


# --- Event Types ---

class TestEventTypes:
    def test_event_type_values(self):
        assert TaskEventType.TASK_CREATED.value == "task_created"
        assert TaskEventType.TASK_QUEUED.value == "task_queued"
        assert TaskEventType.TASK_STARTED.value == "task_started"
        assert TaskEventType.TASK_PAUSED.value == "task_paused"
        assert TaskEventType.TASK_RESUMED.value == "task_resumed"
        assert TaskEventType.TASK_CANCELLED.value == "task_cancelled"
        assert TaskEventType.TASK_TIMEOUT.value == "task_timeout"
        assert TaskEventType.TASK_RETRIED.value == "task_retried"
        assert TaskEventType.TASK_COMPLETED.value == "task_completed"
        assert TaskEventType.TASK_FAILED.value == "task_failed"


# --- State Machine ---

class TestStateMachine:
    def test_all_states(self):
        values = {s.value for s in TaskStatus}
        assert len(values) == 8

    def test_pending_transitions(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.can_transition("queued")
        assert r.can_transition("running")
        assert not r.can_transition("paused")

    def test_running_transitions(self):
        r = TaskRecord(task_id="t", task="x", status=TaskStatus.RUNNING)
        for target in ["paused", "completed", "failed", "cancelled", "timeout"]:
            assert r.can_transition(target), f"running -> {target}"

    def test_terminal_states_limited(self):
        for status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.TIMEOUT]:
            r = TaskRecord(task_id="t", task="x", status=status)
            assert r.can_transition("queued"), f"{status.value} -> queued"
            assert not r.can_transition("running"), f"{status.value} -> running (should be via queued)"


# --- API Integration ---

class TestAPIIntegration:
    @pytest.mark.asyncio
    async def test_list_tasks(self):
        runtime = get_runtime()
        runtime.create_task("t1")
        runtime.create_task("t2")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tasks")
        assert resp.status_code == 200
        assert len(resp.json()["tasks"]) == 2

    @pytest.mark.asyncio
    async def test_queue_status_api(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tasks/queue/status")
        assert resp.status_code == 200
        assert "max_concurrent" in resp.json()

    @pytest.mark.asyncio
    async def test_create_task_api(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/tasks", json={"task": "test"})
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_request_id_in_response(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert "x-request-id" in resp.headers

# --- TaskRecord Dict ---

class TestTaskRecordDict:
    def test_to_dict_basic(self):
        r = TaskRecord(task_id="t1", task="test")
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["task"] == "test"
        assert d["status"] == "pending"

    def test_to_dict_new_fields(self):
        r = TaskRecord(task_id="t1", task="test")
        d = r.to_dict()
        assert "attempt" in d
        assert "max_iterations" in d
        assert "timeout_seconds" in d

    def test_to_dict_error_message(self):
        r = TaskRecord(task_id="t1", task="test", error_message="bad")
        d = r.to_dict()
        assert d["error_message"] == "bad"

    def test_to_dict_no_error_when_none(self):
        r = TaskRecord(task_id="t1", task="test")
        d = r.to_dict()
        assert "error_message" not in d


# --- Event Store Edge Cases ---

class TestEventStoreEdgeCases:
    def test_publish_with_payload(self):
        store = TaskEventStore()
        ev = store.publish("t1", "test", "x", payload={"key": "val"})
        assert ev.payload["key"] == "val"

    def test_publish_with_attempt(self):
        store = TaskEventStore()
        ev = store.publish("t1", "test", "x", attempt=3)
        assert ev.attempt == 3

    def test_get_events_limit(self):
        store = TaskEventStore()
        for i in range(20):
            store.publish("t1", "test", "x")
        events = store.get_events("t1", limit=5)
        assert len(events) == 5

    def test_sequence_never_resets(self):
        store = TaskEventStore()
        store.publish("t1", "a", "x")
        store.publish("t1", "b", "x")
        store.clear("t1")
        store.publish("t1", "c", "x")
        assert store.get_last_sequence("t1") == 3


# --- API Error Responses ---

class TestAPIErrorResponses:
    @pytest.mark.asyncio
    async def test_404_has_error_body(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tasks/nonexistent")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" in body

    @pytest.mark.asyncio
    async def test_events_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tasks/nope/events")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_trace_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tasks/nope/trace")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_history_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tasks/nope/history")
        assert resp.status_code == 404


# --- Timeout ---

class TestTimeout:
    def test_default_no_timeout(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.timeout_seconds is None

    def test_custom_timeout(self):
        r = TaskRecord(task_id="t", task="x", timeout_seconds=60)
        assert r.timeout_seconds == 60

    def test_timeout_in_dict(self):
        r = TaskRecord(task_id="t", task="x", timeout_seconds=120)
        assert r.to_dict()["timeout_seconds"] == 120


# --- Request ID ---

class TestRequestID:
    @pytest.mark.asyncio
    async def test_auto_generated(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        rid = resp.headers.get("x-request-id")
        assert rid is not None
        assert len(rid) > 10

    @pytest.mark.asyncio
    async def test_client_provided(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/", headers={"X-Request-ID": "custom-123"})
        assert resp.headers["x-request-id"] == "custom-123"

    @pytest.mark.asyncio
    async def test_unique_per_request(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r1 = await client.get("/")
            r2 = await client.get("/")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]


# --- Batch Operations ---

class TestBatchOperations:
    @pytest.mark.asyncio
    async def test_create_multiple_tasks(self):
        runtime = get_runtime()
        for i in range(5):
            runtime.create_task("task {0}".format(i))
        assert len(runtime.list_tasks()) == 5

    @pytest.mark.asyncio
    async def test_events_isolated_per_task(self):
        runtime = get_runtime()
        r1 = runtime.create_task("t1")
        r2 = runtime.create_task("t2")
        e1 = runtime.get_task_events(r1.task_id)
        e2 = runtime.get_task_events(r2.task_id)
        assert all(ev["task_id"] == r1.task_id for ev in e1)
        assert all(ev["task_id"] == r2.task_id for ev in e2)

    def test_attempt_default_zero(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.attempt == 0

    def test_max_iterations_default(self):
        r = TaskRecord(task_id="t", task="x")
        assert r.max_iterations == 3

    @pytest.mark.asyncio
    async def test_cancel_event_cleared_on_create(self):
        r = TaskRecord(task_id="t", task="x")
        assert not r.cancel_event.is_set()