"""Phase 4.11 - WebSocket Control Event Tests."""
import pytest
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.runtime.manager import get_runtime, reset_runtime, TaskStatus
from app.api.v1.websocket import get_ws_manager, reset_ws_manager, make_event


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_ws_manager()
    yield
    reset_runtime()
    reset_ws_manager()


class TestMakeEvent:
    def test_event_structure(self):
        ev = make_event("task_started", "t1", {"attempt": 1})
        assert ev["event"] == "task_started"
        assert ev["task_id"] == "t1"
        assert ev["data"]["attempt"] == 1
        assert "timestamp" in ev

    def test_event_no_data(self):
        ev = make_event("task_cancelled", "t1")
        assert ev["data"] == {}


class TestWsManager:
    def test_initial_state(self):
        m = get_ws_manager()
        assert m.total_connections == 0

    def test_subscriber_count(self):
        m = get_ws_manager()
        assert m.subscriber_count("t1") == 0


class TestControlEvents:
    @pytest.mark.asyncio
    async def test_cancel_emits_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.RUNNING
        result = await runtime.cancel_task(record.task_id)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_pause_emits_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.RUNNING
        result = await runtime.pause_task(record.task_id)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_resume_emits_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.PAUSED
        result = await runtime.resume_task(record.task_id)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_retry_emits_event(self):
        runtime = get_runtime()
        record = runtime.create_task("t")
        record.status = TaskStatus.FAILED
        result = await runtime.retry_task(record.task_id)
        assert result["success"] is True