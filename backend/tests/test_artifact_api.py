"""
Phase 4.8 tests - Artifact API
Covers: GET artifacts, empty workspace, 404, response structure, multiple items.
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


@pytest.mark.asyncio
async def test_artifacts_404_for_missing_task():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/nonexistent/artifacts")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_artifacts_empty_for_new_task():
    runtime = get_runtime()
    record = runtime.create_task("test task")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/{0}/artifacts".format(record.task_id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == record.task_id
    assert data["artifacts"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_artifacts_returns_workspace_items():
    runtime = get_runtime()
    record = runtime.create_task("test task")
    tid = record.task_id
    from app.workspace.models import WorkspaceItem
    runtime.workspace_manager.create_workspace(tid)
    runtime.workspace_manager.add_item(tid, WorkspaceItem(
        name="report",
        type="text",
        content="AI trends analysis",
        owner="researcher",
        metadata={"task_id": tid, "step_id": "research"},
    ))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/{0}/artifacts".format(tid))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["artifacts"][0]["name"] == "report"

@pytest.mark.asyncio
async def test_artifacts_response_structure():
    runtime = get_runtime()
    record = runtime.create_task("test task")
    tid = record.task_id
    from app.workspace.models import WorkspaceItem
    runtime.workspace_manager.create_workspace(tid)
    runtime.workspace_manager.add_item(tid, WorkspaceItem(
        name="analysis",
        type="json",
        content="{\"score\": 8}",
        owner="analyst",
    ))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/{0}/artifacts".format(tid))
    data = resp.json()
    assert "task_id" in data
    assert "artifacts" in data
    assert "total" in data
    art = data["artifacts"][0]
    assert "id" in art
    assert "name" in art
    assert "type" in art
    assert "content" in art
    assert "owner" in art
    assert "metadata" in art
    assert "created_at" in art

@pytest.mark.asyncio
async def test_artifacts_multiple_items():
    runtime = get_runtime()
    record = runtime.create_task("multi test")
    tid = record.task_id
    from app.workspace.models import WorkspaceItem
    runtime.workspace_manager.create_workspace(tid)
    for i in range(5):
        runtime.workspace_manager.add_item(tid, WorkspaceItem(
            name="item_{0}".format(i),
            type="text",
            content="content_{0}".format(i),
            owner="agent",
        ))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/{0}/artifacts".format(tid))
    data = resp.json()
    assert data["total"] == 5
    assert len(data["artifacts"]) == 5