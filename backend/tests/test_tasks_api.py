"""
Phase 4.1 测试 — Tasks API
覆盖：
- POST /api/v1/tasks 创建任务
- GET  /api/v1/tasks 列出任务
- GET  /api/v1/tasks/{task_id} 查询任务
- GET  /api/v1/tasks/{task_id}/trace 查询 Trace
- GET  /api/v1/tasks/{task_id}/history 查询历史
- 错误处理
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.runtime.manager import get_runtime, reset_runtime


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    yield
    reset_runtime()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestCreateTask:
    async def test_create_task_returns_201(self):
        async with _client() as c:
            resp = await c.post("/api/v1/tasks", json={"task": "搜索AI新闻"})
        assert resp.status_code == 201
        data = resp.json()
        assert "task_id" in data
        assert data["task"] == "搜索AI新闻"
        assert data["status"] == "pending"

    async def test_create_task_with_iterations(self):
        async with _client() as c:
            resp = await c.post("/api/v1/tasks", json={"task": "test", "max_iterations": 5})
        assert resp.status_code == 201
        assert resp.json()["task_id"].startswith("task-")

    async def test_create_task_empty_rejected(self):
        async with _client() as c:
            resp = await c.post("/api/v1/tasks", json={"task": ""})
        assert resp.status_code == 422

    async def test_create_task_missing_field(self):
        async with _client() as c:
            resp = await c.post("/api/v1/tasks", json={})
        assert resp.status_code == 422


class TestListTasks:
    async def test_list_tasks_empty(self):
        async with _client() as c:
            resp = await c.get("/api/v1/tasks")
        assert resp.status_code == 200
        assert resp.json()["tasks"] == []

    async def test_list_tasks_after_create(self):
        async with _client() as c:
            await c.post("/api/v1/tasks", json={"task": "task1"})
            await c.post("/api/v1/tasks", json={"task": "task2"})
            resp = await c.get("/api/v1/tasks")
        data = resp.json()
        assert len(data["tasks"]) == 2


class TestGetTask:
    async def test_get_task_not_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/tasks/task-nonexist")
        assert resp.status_code == 404

    async def test_get_task_after_create(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "test"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["status"] == "pending"


class TestTaskTrace:
    async def test_trace_not_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/tasks/nonexist/trace")
        assert resp.status_code == 404

    async def test_trace_after_create(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "test"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/trace")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "total" in data


class TestTaskHistory:
    async def test_history_not_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/tasks/nonexist/history")
        assert resp.status_code == 404

    async def test_history_after_create(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "test"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data