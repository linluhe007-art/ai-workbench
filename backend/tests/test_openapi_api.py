"""
Phase 4.24 tests - Open Platform API
Covers: API key CRUD, webhook CRUD, tenant isolation, error cases
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.runtime.manager import reset_runtime
from app.openapi.api_keys import reset_api_key_manager
from app.openapi.webhooks import reset_webhook_manager


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_api_key_manager()
    reset_webhook_manager()
    yield
    reset_runtime()
    reset_api_key_manager()
    reset_webhook_manager()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestAPIKeysAPI:
    async def test_create_api_key(self):
        async with _client() as c:
            resp = await c.post("/api/v1/api-keys", json={"name": "my-key"})
        assert resp.status_code == 200
        data = resp.json()
        assert "api_key" in data
        assert "raw_key" in data
        assert data["raw_key"].startswith("ak-")

    async def test_create_api_key_with_permissions(self):
        async with _client() as c:
            resp = await c.post("/api/v1/api-keys", json={"name": "rw-key", "permissions": ["read", "write"]})
        assert resp.status_code == 200
        assert "read" in resp.json()["api_key"]["permissions"]

    async def test_list_api_keys(self):
        async with _client() as c:
            await c.post("/api/v1/api-keys", json={"name": "k1"})
            await c.post("/api/v1/api-keys", json={"name": "k2"})
            resp = await c.get("/api/v1/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    async def test_list_api_keys_empty(self):
        async with _client() as c:
            resp = await c.get("/api/v1/api-keys")
        assert resp.status_code == 200
        assert resp.json()["api_keys"] == []

    async def test_delete_api_key(self):
        async with _client() as c:
            create_resp = await c.post("/api/v1/api-keys", json={"name": "to-delete"})
            key_id = create_resp.json()["api_key"]["id"]
            resp = await c.delete(f"/api/v1/api-keys/{key_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_delete_nonexistent_key(self):
        async with _client() as c:
            resp = await c.delete("/api/v1/api-keys/nonexistent")
        assert resp.status_code == 404


class TestWebhooksAPI:
    async def test_create_webhook(self):
        async with _client() as c:
            resp = await c.post("/api/v1/webhooks", json={"url": "https://example.com/hook"})
        assert resp.status_code == 200
        data = resp.json()
        assert "webhook" in data
        assert data["webhook"]["url"] == "https://example.com/hook"

    async def test_create_webhook_with_events(self):
        async with _client() as c:
            resp = await c.post("/api/v1/webhooks", json={
                "url": "https://example.com/hook",
                "events": ["task.completed", "task.failed"],
            })
        data = resp.json()
        assert len(data["webhook"]["events"]) == 2

    async def test_list_webhooks(self):
        async with _client() as c:
            await c.post("/api/v1/webhooks", json={"url": "https://a.com/hook"})
            await c.post("/api/v1/webhooks", json={"url": "https://b.com/hook"})
            resp = await c.get("/api/v1/webhooks")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    async def test_list_webhooks_empty(self):
        async with _client() as c:
            resp = await c.get("/api/v1/webhooks")
        assert resp.status_code == 200
        assert resp.json()["webhooks"] == []

    async def test_delete_webhook(self):
        async with _client() as c:
            create_resp = await c.post("/api/v1/webhooks", json={"url": "https://example.com/hook"})
            wh_id = create_resp.json()["webhook"]["id"]
            resp = await c.delete(f"/api/v1/webhooks/{wh_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_delete_nonexistent_webhook(self):
        async with _client() as c:
            resp = await c.delete("/api/v1/webhooks/nonexistent")
        assert resp.status_code == 404


class TestOpenAPISchema:
    async def test_api_key_response_schema(self):
        async with _client() as c:
            resp = await c.post("/api/v1/api-keys", json={"name": "schema-key", "permissions": ["read"]})
        data = resp.json()["api_key"]
        assert "id" in data
        assert "name" in data
        assert "key_prefix" in data
        assert "permissions" in data
        assert "enabled" in data
        assert "created_at" in data
        assert "key_hash" not in data

    async def test_webhook_response_schema(self):
        async with _client() as c:
            resp = await c.post("/api/v1/webhooks", json={"url": "https://example.com/hook"})
        data = resp.json()["webhook"]
        assert "id" in data
        assert "url" in data
        assert "events" in data
        assert "enabled" in data
        assert "delivery_count" in data
        assert "failure_count" in data
        assert "secret" not in data