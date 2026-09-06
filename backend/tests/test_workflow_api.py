"""
Phase 4.6 测试 — Workflow API
覆盖：
- GET /api/v1/tasks/{task_id}/workflow
- DAG 节点结构
- 依赖关系
- step 状态推断
- 404 处理
- 多步骤 DAG
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


# ── Basic Workflow ────────────────────────────────────────────


class TestGetWorkflow:
    async def test_workflow_not_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/tasks/nonexist/workflow")
        assert resp.status_code == 404

    async def test_workflow_after_create(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert "intent" in data
        assert "steps" in data

    async def test_workflow_has_steps(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "研究AI趋势并写报告"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        data = resp.json()
        assert data["total_steps"] >= 1
        assert len(data["steps"]) == data["total_steps"]


# ── Step Structure ────────────────────────────────────────────


class TestStepStructure:
    async def test_step_has_required_fields(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        for step in resp.json()["steps"]:
            assert "id" in step
            assert "type" in step
            assert "description" in step
            assert "agent" in step
            assert "depends_on" in step
            assert "status" in step

    async def test_step_has_timing_fields(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        for step in resp.json()["steps"]:
            assert "started_at" in step
            assert "finished_at" in step
            assert "duration" in step

    async def test_step_status_is_valid(self):
        valid_statuses = {"pending", "running", "success", "failed", "skipped"}
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        for step in resp.json()["steps"]:
            assert step["status"] in valid_statuses


# ── Dependencies ──────────────────────────────────────────────


class TestDependencies:
    async def test_depends_on_is_list(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "研究并写报告"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        for step in resp.json()["steps"]:
            assert isinstance(step["depends_on"], list)

    async def test_multi_step_has_dependencies(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "研究AI趋势并写报告"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        steps = resp.json()["steps"]
        if len(steps) > 1:
            # At least one step should have dependencies
            has_deps = any(len(s["depends_on"]) > 0 for s in steps)
            assert has_deps or len(steps) == 1

    async def test_first_step_no_dependencies(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        steps = resp.json()["steps"]
        if steps:
            # First step (research) should have no deps
            research_steps = [s for s in steps if s["id"] == "research"]
            if research_steps:
                assert research_steps[0]["depends_on"] == []


# ── Status Inference ──────────────────────────────────────────


class TestStatusInference:
    async def test_initial_status_pending(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        # Steps should be pending since we haven't executed
        for step in resp.json()["steps"]:
            assert step["status"] == "pending"

    async def test_pending_step_has_null_times(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        for step in resp.json()["steps"]:
            if step["status"] == "pending":
                assert step["started_at"] is None
                assert step["finished_at"] is None

    async def test_pending_step_zero_duration(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        for step in resp.json()["steps"]:
            if step["status"] == "pending":
                assert step["duration"] == 0


# ── Intent ────────────────────────────────────────────────────


class TestIntent:
    async def test_workflow_intent(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        assert resp.json()["intent"] == "搜索资料"

    async def test_workflow_intent_long_task(self):
        task_text = "研究2026年AI行业最新趋势并撰写深度分析报告"
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": task_text})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        assert resp.json()["intent"] == task_text


# ── DAG Topology ──────────────────────────────────────────────


class TestDAGTopology:
    async def test_research_task_single_step(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        steps = resp.json()["steps"]
        assert len(steps) >= 1
        ids = [s["id"] for s in steps]
        assert "research" in ids

    async def test_writing_task_multi_step(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "写一篇AI报告"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        steps = resp.json()["steps"]
        assert len(steps) >= 2

    async def test_step_ids_unique(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "研究AI趋势并写报告"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        ids = [s["id"] for s in resp.json()["steps"]]
        assert len(ids) == len(set(ids))

    async def test_agent_field_non_empty(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        for step in resp.json()["steps"]:
            assert step["agent"]
            assert len(step["agent"]) > 0

# ── Edge Cases ────────────────────────────────────────────────


class TestEdgeCases:
    async def test_workflow_total_steps_matches_list(self):
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "研究AI趋势并写报告"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        data = resp.json()
        assert data["total_steps"] == len(data["steps"])

    async def test_workflow_step_type_is_valid(self):
        valid_types = {"research", "analysis", "writing", "image", "seo", "chat", "custom"}
        async with _client() as c:
            create = await c.post("/api/v1/tasks", json={"task": "搜索资料"})
            task_id = create.json()["task_id"]
            resp = await c.get(f"/api/v1/tasks/{task_id}/workflow")
        for step in resp.json()["steps"]:
            assert step["type"] in valid_types