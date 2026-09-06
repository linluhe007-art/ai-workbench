"""
Phase 4.9 tests - Extended Artifact API + Workspace Manager
Covers:
- GET /artifacts/{id}
- DELETE /artifacts/{id}
- POST /artifacts/{id}/rename
- 404 for missing artifacts
- task/artifact isolation
- metadata fields
- workspace manager find_item_globally
- workspace manager rename_item
- workspace manager update_item_metadata
- multiple artifacts across workspaces
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.runtime.manager import get_runtime, reset_runtime
from app.workspace.manager import WorkspaceManager
from app.workspace.models import WorkspaceItem


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    yield
    reset_runtime()


def _seed_artifact(runtime, task_id="t1", name="report", art_type="text", content="hello", owner="agent"):
    """Helper to create a task and add an artifact."""
    record = runtime.create_task("seed task")
    tid = task_id if task_id == record.task_id else task_id
    if task_id != record.task_id:
        runtime.create_task("another")
    runtime.workspace_manager.create_workspace(task_id)
    return runtime.workspace_manager.save_artifact(
        workspace_id=task_id,
        owner=owner,
        name=name,
        content=content,
        item_type=art_type,
        metadata={"task_id": task_id, "step_id": "research", "created_by": owner},
    )


# --- GET /artifacts/{artifact_id} ---

@pytest.mark.asyncio
async def test_get_artifact_by_id():
    runtime = get_runtime()
    record = runtime.create_task("t")
    tid = record.task_id
    runtime.workspace_manager.create_workspace(tid)
    item = runtime.workspace_manager.save_artifact(tid, "agent", "r1", "content", "text", {"task_id": tid})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/artifacts/{0}".format(item.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == item.id
    assert data["name"] == "r1"
    assert data["workspace_id"] == tid

@pytest.mark.asyncio
async def test_get_artifact_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/artifacts/nonexistent")
    assert resp.status_code == 404


# --- DELETE /artifacts/{artifact_id} ---

@pytest.mark.asyncio
async def test_delete_artifact():
    runtime = get_runtime()
    record = runtime.create_task("t")
    tid = record.task_id
    runtime.workspace_manager.create_workspace(tid)
    item = runtime.workspace_manager.save_artifact(tid, "agent", "r1", "content", "text")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/v1/artifacts/{0}".format(item.id))
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True
    assert data["artifact_id"] == item.id
    # Verify it is gone
    assert runtime.workspace_manager.get_item(tid, item.id) is None

@pytest.mark.asyncio
async def test_delete_artifact_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/api/v1/artifacts/nonexistent")
    assert resp.status_code == 404


# --- POST /artifacts/{artifact_id}/rename ---

@pytest.mark.asyncio
async def test_rename_artifact():
    runtime = get_runtime()
    record = runtime.create_task("t")
    tid = record.task_id
    runtime.workspace_manager.create_workspace(tid)
    item = runtime.workspace_manager.save_artifact(tid, "agent", "old_name", "content", "text")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/artifacts/{0}/rename".format(item.id), json={"name": "new_name"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "new_name"

@pytest.mark.asyncio
async def test_rename_artifact_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/artifacts/nonexistent/rename", json={"name": "x"})
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_rename_artifact_empty_name():
    runtime = get_runtime()
    record = runtime.create_task("t")
    tid = record.task_id
    runtime.workspace_manager.create_workspace(tid)
    item = runtime.workspace_manager.save_artifact(tid, "agent", "name", "content", "text")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/artifacts/{0}/rename".format(item.id), json={"name": ""})
    assert resp.status_code == 422


# --- Isolation ---

@pytest.mark.asyncio
async def test_artifact_isolation_between_tasks():
    runtime = get_runtime()
    r1 = runtime.create_task("t1")
    r2 = runtime.create_task("t2")
    t1, t2 = r1.task_id, r2.task_id
    runtime.workspace_manager.create_workspace(t1)
    runtime.workspace_manager.create_workspace(t2)
    i1 = runtime.workspace_manager.save_artifact(t1, "a", "art1", "c1", "text", {"task_id": t1})
    i2 = runtime.workspace_manager.save_artifact(t2, "b", "art2", "c2", "text", {"task_id": t2})
    # t1 only sees its own
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/{0}/artifacts".format(t1))
    data = resp.json()
    assert data["total"] == 1
    assert data["artifacts"][0]["name"] == "art1"

@pytest.mark.asyncio
async def test_delete_does_not_affect_other_task():
    runtime = get_runtime()
    r1 = runtime.create_task("t1")
    r2 = runtime.create_task("t2")
    t1, t2 = r1.task_id, r2.task_id
    runtime.workspace_manager.create_workspace(t1)
    runtime.workspace_manager.create_workspace(t2)
    i1 = runtime.workspace_manager.save_artifact(t1, "a", "art1", "c1", "text")
    i2 = runtime.workspace_manager.save_artifact(t2, "b", "art2", "c2", "text")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.delete("/api/v1/artifacts/{0}".format(i1.id))
    # i2 still exists
    assert runtime.workspace_manager.get_item(t2, i2.id) is not None


# --- Metadata ---

@pytest.mark.asyncio
async def test_artifact_metadata_fields():
    runtime = get_runtime()
    record = runtime.create_task("t")
    tid = record.task_id
    runtime.workspace_manager.create_workspace(tid)
    item = runtime.workspace_manager.save_artifact(
        tid, "researcher", "report", "content", "text",
        {"task_id": tid, "step_id": "research", "created_by": "researcher"}
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/artifacts/{0}".format(item.id))
    data = resp.json()
    assert data["metadata"]["task_id"] == tid
    assert data["metadata"]["step_id"] == "research"
    assert data["metadata"]["created_by"] == "researcher"


# --- Workspace Manager direct tests ---

def test_find_item_globally():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    item = wm.save_artifact("ws1", "owner", "name", "content", "text")
    result = wm.find_item_globally(item.id)
    assert result is not None
    ws_id, found = result
    assert ws_id == "ws1"
    assert found.id == item.id

def test_find_item_globally_not_found():
    wm = WorkspaceManager()
    assert wm.find_item_globally("nonexistent") is None

def test_find_item_globally_across_workspaces():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    wm.create_workspace("ws2")
    i1 = wm.save_artifact("ws1", "o", "n1", "c", "text")
    i2 = wm.save_artifact("ws2", "o", "n2", "c", "text")
    r = wm.find_item_globally(i2.id)
    assert r is not None
    assert r[0] == "ws2"

def test_rename_item():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    item = wm.save_artifact("ws1", "o", "old", "c", "text")
    updated = wm.rename_item("ws1", item.id, "new")
    assert updated is not None
    assert updated.name == "new"

def test_rename_item_not_found():
    wm = WorkspaceManager()
    assert wm.rename_item("ws1", "bad", "new") is None

def test_update_item_metadata():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    item = wm.save_artifact("ws1", "o", "n", "c", "text", {"a": 1})
    updated = wm.update_item_metadata("ws1", item.id, {"b": 2})
    assert updated is not None
    assert updated.metadata["a"] == 1
    assert updated.metadata["b"] == 2

def test_get_all_workspaces():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    wm.create_workspace("ws2")
    ws = wm.get_all_workspaces()
    assert "ws1" in ws
    assert "ws2" in ws

def test_delete_item_returns_false_when_missing():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    assert wm.delete_item("ws1", "nonexistent") is False
@pytest.mark.asyncio
async def test_rename_preserves_other_fields():
    runtime = get_runtime()
    record = runtime.create_task("t")
    tid = record.task_id
    runtime.workspace_manager.create_workspace(tid)
    item = runtime.workspace_manager.save_artifact(tid, "agent", "orig", "content", "json", {"task_id": tid})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/artifacts/{0}/rename".format(item.id), json={"name": "renamed"})
    data = resp.json()
    assert data["name"] == "renamed"
    assert data["type"] == "json"
    assert data["owner"] == "agent"
    assert data["content"] == "content"

def test_workspace_manager_create_idempotent():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    wm.create_workspace("ws1")  # should not error
    assert wm.workspace_exists("ws1")