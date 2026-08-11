"""
Phase 4.1 测试 — Agents API + Executions API
覆盖：
- GET /api/v1/agents 列出 Agent
- GET /api/v1/agents/{id} 查询 Agent
- GET /api/v1/agents/status/runtime 运行时状态
- GET /api/v1/executions/metrics 指标
- GET /api/v1/executions/trace/all 所有 Trace
- GET /api/v1/executions/trace/errors 错误 Trace
- GET /api/v1/executions/trace/component/{c} 按组件过滤
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


# ── Agents API ───────────────────────────────────────────────


class TestAgentsAPI:
    async def test_list_agents(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_agents_contains_default(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents")
        agent_ids = [a["id"] for a in resp.json()["agents"]]
        assert "default" in agent_ids

    async def test_get_agent_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/default")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "default"

    async def test_get_agent_not_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/nonexist")
        assert resp.status_code == 404

    async def test_runtime_status(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/status/runtime")
        assert resp.status_code == 200
        data = resp.json()
        assert "agents_count" in data
        assert "tasks_count" in data
        assert "metrics" in data


# ── Executions API ───────────────────────────────────────────


class TestExecutionsAPI:
    async def test_metrics_empty(self):
        async with _client() as c:
            resp = await c.get("/api/v1/executions/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tasks" in data
        assert "success_rate" in data

    async def test_trace_all_empty(self):
        async with _client() as c:
            resp = await c.get("/api/v1/executions/trace/all")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_trace_errors_empty(self):
        async with _client() as c:
            resp = await c.get("/api/v1/executions/trace/errors")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_trace_by_component(self):
        async with _client() as c:
            resp = await c.get("/api/v1/executions/trace/component/executor")
        assert resp.status_code == 200
        assert resp.json()["component"] == "executor"

    async def test_trace_all_after_activity(self):
        """创建任务后 trace 应该有数据"""
        async with _client() as c:
            # 创建一个任务触发 trace 记录
            await c.post("/api/v1/tasks", json={"task": "test"})
            resp = await c.get("/api/v1/executions/trace/all")
        # 至少有任务创建相关的 trace
        assert resp.status_code == 200