"""
Phase 4.4 测试 — Workspaces API
覆盖：
- POST /api/v1/workspaces 创建工作空间
- POST /api/v1/workspaces/{id}/items 添加 Artifact
- GET  /api/v1/workspaces/{id}/items 列出 Artifact
- GET  /api/v1/workspaces/{id}/items/{item_id} 获取单个
- DELETE /api/v1/workspaces/{id}/items/{item_id} 删除
- 错误处理
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.v1.workspaces import reset_ws_manager


@pytest.fixture(autouse=True)
def _reset():
    reset_ws_manager()
    yield
    reset_ws_manager()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Create Workspace ─────────────────────────────────────────


class TestCreateWorkspace:
    async def test_create_workspace(self):
        async with _client() as c:
            resp = await c.post("/api/v1/workspaces", json={"task_id": "task-1"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["workspace_id"] == "task-1"

    async def test_create_workspace_empty_task_id(self):
        async with _client() as c:
            resp = await c.post("/api/v1/workspaces", json={"task_id": ""})
        assert resp.status_code == 422

    async def test_create_workspace_missing_field(self):
        async with _client() as c:
            resp = await c.post("/api/v1/workspaces", json={})
        assert resp.status_code == 422


# ── Add Item ─────────────────────────────────────────────────


class TestAddItem:
    async def test_add_item(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.post("/api/v1/workspaces/ws-1/items", json={
                "name": "research_result",
                "type": "text",
                "content": "AI trends summary",
                "owner": "research-agent",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "research_result"
        assert data["owner"] == "research-agent"
        assert "id" in data

    async def test_add_item_with_metadata(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.post("/api/v1/workspaces/ws-1/items", json={
                "name": "report",
                "type": "dict",
                "content": {"title": "AI Report", "sections": ["intro", "analysis"]},
                "owner": "writing-agent",
                "metadata": {"version": 1, "language": "zh"},
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["metadata"]["version"] == 1

    async def test_add_item_default_values(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.post("/api/v1/workspaces/ws-1/items", json={
                "name": "minimal",
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "text"
        assert data["owner"] == "user"


# ── List Items ───────────────────────────────────────────────


class TestListItems:
    async def test_list_empty(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.get("/api/v1/workspaces/ws-1/items")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_after_add(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            await c.post("/api/v1/workspaces/ws-1/items", json={"name": "item-1"})
            await c.post("/api/v1/workspaces/ws-1/items", json={"name": "item-2"})
            resp = await c.get("/api/v1/workspaces/ws-1/items")
        data = resp.json()
        assert data["total"] == 2
        names = [i["name"] for i in data["items"]]
        assert "item-1" in names

    async def test_list_nonexistent_workspace(self):
        async with _client() as c:
            resp = await c.get("/api/v1/workspaces/no-such/items")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ── Get Item ─────────────────────────────────────────────────


class TestGetItem:
    async def test_get_item(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            add_resp = await c.post("/api/v1/workspaces/ws-1/items", json={"name": "doc", "content": "hello"})
            item_id = add_resp.json()["id"]
            resp = await c.get(f"/api/v1/workspaces/ws-1/items/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["content"] == "hello"

    async def test_get_item_not_found(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.get("/api/v1/workspaces/ws-1/items/nonexist")
        assert resp.status_code == 404


# ── Delete Item ──────────────────────────────────────────────


class TestDeleteItem:
    async def test_delete_item(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            add_resp = await c.post("/api/v1/workspaces/ws-1/items", json={"name": "temp"})
            item_id = add_resp.json()["id"]
            del_resp = await c.delete(f"/api/v1/workspaces/ws-1/items/{item_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

        # Verify deleted
        async with _client() as c:
            get_resp = await c.get(f"/api/v1/workspaces/ws-1/items/{item_id}")
        assert get_resp.status_code == 404

    async def test_delete_not_found(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.delete("/api/v1/workspaces/ws-1/items/nonexist")
        assert resp.status_code == 404

    async def test_delete_reduces_count(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            r1 = await c.post("/api/v1/workspaces/ws-1/items", json={"name": "a"})
            await c.post("/api/v1/workspaces/ws-1/items", json={"name": "b"})
            await c.delete(f"/api/v1/workspaces/ws-1/items/{r1.json()['id']}")
            list_resp = await c.get("/api/v1/workspaces/ws-1/items")
        assert list_resp.json()["total"] == 1


# ── Isolation ────────────────────────────────────────────────


class TestWorkspaceIsolation:
    async def test_items_isolated_by_workspace(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            await c.post("/api/v1/workspaces", json={"task_id": "ws-2"})
            await c.post("/api/v1/workspaces/ws-1/items", json={"name": "item-ws1"})
            await c.post("/api/v1/workspaces/ws-2/items", json={"name": "item-ws2"})

            r1 = await c.get("/api/v1/workspaces/ws-1/items")
            r2 = await c.get("/api/v1/workspaces/ws-2/items")
        assert r1.json()["total"] == 1
        assert r2.json()["total"] == 1
        assert r1.json()["items"][0]["name"] == "item-ws1"
        assert r2.json()["items"][0]["name"] == "item-ws2"

    async def test_delete_does_not_affect_other_workspace(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            await c.post("/api/v1/workspaces", json={"task_id": "ws-2"})
            r1 = await c.post("/api/v1/workspaces/ws-1/items", json={"name": "shared-name"})
            await c.post("/api/v1/workspaces/ws-2/items", json={"name": "shared-name"})
            item_id = r1.json()["id"]

            await c.delete(f"/api/v1/workspaces/ws-1/items/{item_id}")
            r2 = await c.get("/api/v1/workspaces/ws-2/items")
        assert r2.json()["total"] == 1


# ── Content Types ────────────────────────────────────────────


class TestContentTypes:
    async def test_text_content(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.post("/api/v1/workspaces/ws-1/items", json={
                "name": "text", "type": "text", "content": "plain text"
            })
        assert resp.json()["content"] == "plain text"

    async def test_dict_content(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.post("/api/v1/workspaces/ws-1/items", json={
                "name": "dict", "type": "dict", "content": {"key": "value"}
            })
        assert resp.json()["content"]["key"] == "value"

    async def test_list_content(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            resp = await c.post("/api/v1/workspaces/ws-1/items", json={
                "name": "list", "type": "list", "content": [1, 2, 3]
            })
        assert resp.json()["content"] == [1, 2, 3]
# ── Multiple Items CRUD ──────────────────────────────────────


class TestMultipleItems:
    async def test_multiple_items_order(self):
        async with _client() as c:
            await c.post("/api/v1/workspaces", json={"task_id": "ws-1"})
            await c.post("/api/v1/workspaces/ws-1/items", json={"name": "first"})
            await c.post("/api/v1/workspaces/ws-1/items", json={"name": "second"})
            await c.post("/api/v1/workspaces/ws-1/items", json={"name": "third"})
            resp = await c.get("/api/v1/workspaces/ws-1/items")
        assert resp.json()["total"] == 3