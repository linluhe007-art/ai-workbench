"""Phase 4.12 - Events API, Middleware, Error Model tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.runtime.manager import get_runtime, reset_runtime, TaskStatus
from app.api.v1.websocket import reset_ws_manager


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_ws_manager()
    yield
    reset_runtime()
    reset_ws_manager()


# --- Events API ---

class TestEventsAPI:
    @pytest.mark.asyncio
    async def test_get_events_empty(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/tasks/{record.task_id}/events")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == record.task_id
        assert "events" in data
        assert "last_sequence" in data

    @pytest.mark.asyncio
    async def test_get_events_has_created_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/tasks/{record.task_id}/events")
        data = resp.json()
        assert data["total"] >= 1
        assert data["events"][0]["event_type"] == "task_created"

    @pytest.mark.asyncio
    async def test_get_events_since_sequence(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        runtime.event_store.publish(record.task_id, "test", "x")
        runtime.event_store.publish(record.task_id, "test2", "x")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/tasks/{record.task_id}/events", params={"since_sequence": 1})
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_events_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tasks/nonexistent/events")
        assert resp.status_code == 404


# --- Request ID Middleware ---

class TestRequestIDMiddleware:
    @pytest.mark.asyncio
    async def test_generates_request_id(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/")
        assert "x-request-id" in resp.headers
        assert len(resp.headers["x-request-id"]) > 0

    @pytest.mark.asyncio
    async def test_preserves_client_request_id(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/", headers={"X-Request-ID": "my-id-123"})
        assert resp.headers["x-request-id"] == "my-id-123"


# --- Error Model ---

class TestErrorModel:
    def test_error_code_constants(self):
        from app.api.errors import ErrorCode
        assert ErrorCode.TASK_NOT_FOUND == "TASK_NOT_FOUND"
        assert ErrorCode.INVALID_TASK_STATE == "INVALID_TASK_STATE"
        assert ErrorCode.TASK_ALREADY_COMPLETED == "TASK_ALREADY_COMPLETED"
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_cancel_returns_409_on_invalid_state(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.COMPLETED
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/tasks/{record.task_id}/cancel")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_pause_returns_409_on_invalid_state(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.FAILED
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/v1/tasks/{record.task_id}/pause")
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_404_for_missing_task(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tasks/nonexistent")
        assert resp.status_code == 404


# --- Event Integration with Runtime ---

class TestEventIntegration:
    @pytest.mark.asyncio
    async def test_create_publishes_event(self):
        runtime = get_runtime()
        record = runtime.create_task("test")
        events = runtime.get_task_events(record.task_id)
        assert len(events) >= 1
        assert events[0]["event_type"] == "task_created"

    @pytest.mark.asyncio
    async def test_cancel_publishes_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.RUNNING
        await runtime.cancel_task(record.task_id)
        events = runtime.get_task_events(record.task_id)
        types = [e["event_type"] for e in events]
        assert "task_cancelled" in types

    @pytest.mark.asyncio
    async def test_pause_publishes_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.RUNNING
        await runtime.pause_task(record.task_id)
        events = runtime.get_task_events(record.task_id)
        types = [e["event_type"] for e in events]
        assert "task_paused" in types

    @pytest.mark.asyncio
    async def test_resume_publishes_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.PAUSED
        await runtime.resume_task(record.task_id)
        events = runtime.get_task_events(record.task_id)
        types = [e["event_type"] for e in events]
        assert "task_resumed" in types

    @pytest.mark.asyncio
    async def test_retry_publishes_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.FAILED
        await runtime.retry_task(record.task_id)
        events = runtime.get_task_events(record.task_id)
        types = [e["event_type"] for e in events]
        assert "task_retried" in types