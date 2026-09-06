"""
Phase 5.1 tests - Intelligence API
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.runtime.manager import reset_runtime


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    yield
    reset_runtime()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestCommandAPI:
    async def test_command_returns_200(self):
        async with _client() as c:
            resp = await c.post("/api/v1/intelligence/command", json={"prompt": "research AI"})
        assert resp.status_code == 200

    async def test_command_has_intent(self):
        async with _client() as c:
            resp = await c.post("/api/v1/intelligence/command", json={"prompt": "write a report"})
        data = resp.json()
        assert "intent" in data
        assert data["intent"]["task_type"] == "writing"

    async def test_command_has_classification(self):
        async with _client() as c:
            resp = await c.post("/api/v1/intelligence/command", json={"prompt": "search web"})
        data = resp.json()
        assert "classification" in data

    async def test_command_has_task_id(self):
        async with _client() as c:
            resp = await c.post("/api/v1/intelligence/command", json={"prompt": "analyze data"})
        data = resp.json()
        assert "task_id" in data

    async def test_command_has_confidence(self):
        async with _client() as c:
            resp = await c.post("/api/v1/intelligence/command", json={"prompt": "research AI"})
        data = resp.json()
        assert "confidence" in data

    async def test_command_empty_prompt(self):
        async with _client() as c:
            resp = await c.post("/api/v1/intelligence/command", json={"prompt": ""})
        assert resp.status_code == 200

    async def test_command_unknown_type(self):
        async with _client() as c:
            resp = await c.post("/api/v1/intelligence/command", json={"prompt": "xyz nothing"})
        data = resp.json()
        assert data["intent"]["task_type"] == "unknown"

    async def test_command_missing_prompt(self):
        async with _client() as c:
            resp = await c.post("/api/v1/intelligence/command", json={})
        assert resp.status_code == 422


class TestHistoryAPI:
    async def test_history_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/intelligence/history")
        assert resp.status_code == 200

    async def test_history_has_fields(self):
        async with _client() as c:
            await c.post("/api/v1/intelligence/command", json={"prompt": "test"})
            resp = await c.get("/api/v1/intelligence/history")
        data = resp.json()
        assert "history" in data
        assert "total" in data
        assert data["total"] >= 1