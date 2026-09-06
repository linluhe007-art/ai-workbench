"""
Phase 4.10 tests - Artifact Search API + WorkspaceManager.search_items
Covers: empty search, name/content query, case insensitivity, JSON/markdown/URL search,
type/agent/task/workspace/step filters, date filters, multi-filter combos,
sort asc/desc/name/type, pagination, total, isolation, schema.
"""

import pytest
from datetime import datetime, timezone, timedelta
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


@pytest.fixture
def seeded_runtime():
    """Seed a runtime with multiple workspaces and artifacts."""
    runtime = get_runtime()
    r1 = runtime.create_task("task alpha")
    r2 = runtime.create_task("task beta")
    t1, t2 = r1.task_id, r2.task_id
    wm = runtime.workspace_manager
    wm.create_workspace(t1)
    wm.create_workspace(t2)
    # t1 artifacts
    wm.save_artifact(t1, "researcher", "AI Trends Report", "# AI Trends\n\nAnalysis of 2026", "markdown", {"task_id": t1, "step_id": "research", "created_by": "researcher"})
    wm.save_artifact(t1, "analyst", "Score Result", "{\"score\": 8.5}", "json", {"task_id": t1, "step_id": "analysis", "created_by": "analyst"})
    wm.save_artifact(t1, "writer", "Article Draft", "This is the article body text", "text", {"task_id": t1, "step_id": "writing", "created_by": "writer"})
    wm.save_artifact(t1, "researcher", "Source Link", "https://example.com/ai-news", "url", {"task_id": t1, "step_id": "research", "created_by": "researcher"})
    # t2 artifacts
    wm.save_artifact(t2, "researcher", "ML Research", "Machine Learning basics", "text", {"task_id": t2, "step_id": "research", "created_by": "researcher"})
    wm.save_artifact(t2, "writer", "ML Article", "# ML Guide\n\nLearn ML", "markdown", {"task_id": t2, "step_id": "writing", "created_by": "writer"})
    return runtime, t1, t2


# --- Helper ---

async def _search(params: dict):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/artifacts/search", params=params)
    return resp


# --- Empty / Default ---

@pytest.mark.asyncio
async def test_search_empty_db():
    resp = await _search({})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0

@pytest.mark.asyncio
async def test_search_default_params(seeded_runtime):
    resp = await _search({})
    data = resp.json()
    assert data["total"] == 6
    assert data["limit"] == 50
    assert data["offset"] == 0


# --- Query Search ---

@pytest.mark.asyncio
async def test_search_by_name(seeded_runtime):
    resp = await _search({"q": "AI Trends"})
    data = resp.json()
    assert data["total"] >= 1
    names = [i["name"] for i in data["items"]]
    assert any("AI Trends" in n for n in names)

@pytest.mark.asyncio
async def test_search_by_content(seeded_runtime):
    resp = await _search({"q": "Machine Learning"})
    data = resp.json()
    assert data["total"] >= 1

@pytest.mark.asyncio
async def test_search_case_insensitive(seeded_runtime):
    resp = await _search({"q": "ai trends"})
    data = resp.json()
    assert data["total"] >= 1

@pytest.mark.asyncio
async def test_search_json_content(seeded_runtime):
    resp = await _search({"q": "8.5"})
    data = resp.json()
    assert data["total"] >= 1

@pytest.mark.asyncio
async def test_search_markdown_content(seeded_runtime):
    resp = await _search({"q": "AI Trends"})
    data = resp.json()
    assert data["total"] >= 1

@pytest.mark.asyncio
async def test_search_url_content(seeded_runtime):
    resp = await _search({"q": "example.com"})
    data = resp.json()
    assert data["total"] >= 1

@pytest.mark.asyncio
async def test_search_no_match(seeded_runtime):
    resp = await _search({"q": "zzz_nonexistent_zzz"})
    data = resp.json()
    assert data["total"] == 0


# --- Filters ---

@pytest.mark.asyncio
async def test_filter_by_type(seeded_runtime):
    resp = await _search({"type": "markdown"})
    data = resp.json()
    assert data["total"] == 2
    assert all(i["type"] == "markdown" for i in data["items"])

@pytest.mark.asyncio
async def test_filter_by_agent(seeded_runtime):
    resp = await _search({"agent_id": "researcher"})
    data = resp.json()
    assert data["total"] == 3

@pytest.mark.asyncio
async def test_filter_by_task(seeded_runtime: tuple):
    _rt, t1, _t2 = seeded_runtime
    resp = await _search({"task_id": t1})
    data = resp.json()
    assert data["total"] == 4

@pytest.mark.asyncio
async def test_filter_by_workspace(seeded_runtime: tuple):
    _rt, _t1, t2 = seeded_runtime
    resp = await _search({"workspace_id": t2})
    data = resp.json()
    assert data["total"] == 2

@pytest.mark.asyncio
async def test_filter_by_step(seeded_runtime):
    resp = await _search({"step_id": "research"})
    data = resp.json()
    assert data["total"] == 3

@pytest.mark.asyncio
async def test_filter_multi(seeded_runtime):
    resp = await _search({"type": "text", "agent_id": "writer"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Article Draft"


# --- Date Filters ---

@pytest.mark.asyncio
async def test_filter_created_after(seeded_runtime):
    past = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
    resp = await _search({"created_after": past})
    data = resp.json()
    assert data["total"] == 6

@pytest.mark.asyncio
async def test_filter_created_before(seeded_runtime):
    future = datetime(2099, 1, 1, tzinfo=timezone.utc).isoformat()
    resp = await _search({"created_before": future})
    data = resp.json()
    assert data["total"] == 6


# --- Sorting ---

@pytest.mark.asyncio
async def test_sort_by_name_asc(seeded_runtime):
    resp = await _search({"sort_by": "name", "order": "asc"})
    data = resp.json()
    names = [i["name"] for i in data["items"]]
    assert names == sorted(names, key=str.lower)

@pytest.mark.asyncio
async def test_sort_by_name_desc(seeded_runtime):
    resp = await _search({"sort_by": "name", "order": "desc"})
    data = resp.json()
    names = [i["name"] for i in data["items"]]
    assert names == sorted(names, key=str.lower, reverse=True)

@pytest.mark.asyncio
async def test_sort_by_type(seeded_runtime):
    resp = await _search({"sort_by": "type", "order": "asc"})
    data = resp.json()
    types = [i["type"] for i in data["items"]]
    assert types == sorted(types)


# --- Pagination ---

@pytest.mark.asyncio
async def test_pagination_limit(seeded_runtime):
    resp = await _search({"limit": 2})
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 6
    assert data["limit"] == 2

@pytest.mark.asyncio
async def test_pagination_offset(seeded_runtime):
    resp = await _search({"limit": 2, "offset": 2})
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["offset"] == 2

@pytest.mark.asyncio
async def test_pagination_beyond_total(seeded_runtime):
    resp = await _search({"offset": 100})
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 6


# --- Response Schema ---

@pytest.mark.asyncio
async def test_response_schema(seeded_runtime):
    resp = await _search({"limit": 1})
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    item = data["items"][0]
    assert "id" in item
    assert "name" in item
    assert "type" in item
    assert "content" in item
    assert "owner" in item
    assert "metadata" in item
    assert "created_at" in item
    assert "workspace_id" in item


# --- WorkspaceManager direct tests ---

def test_search_items_empty():
    wm = WorkspaceManager()
    items, total = wm.search_items()
    assert items == []
    assert total == 0

def test_search_items_by_type():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    wm.save_artifact("ws1", "o", "n1", "c", "text")
    wm.save_artifact("ws1", "o", "n2", "c", "json")
    items, total = wm.search_items(artifact_type="text")
    assert total == 1
    assert items[0]["type"] == "text"

def test_search_items_by_query():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    wm.save_artifact("ws1", "o", "Report Alpha", "content here", "text")
    wm.save_artifact("ws1", "o", "Beta Doc", "other", "text")
    items, total = wm.search_items(query="alpha")
    assert total == 1

def test_search_items_pagination():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    for i in range(10):
        wm.save_artifact("ws1", "o", "item{0}".format(i), "c", "text")
    items, total = wm.search_items(limit=3, offset=2)
    assert len(items) == 3
    assert total == 10

def test_search_items_isolation():
    wm = WorkspaceManager()
    wm.create_workspace("ws1")
    wm.create_workspace("ws2")
    wm.save_artifact("ws1", "o", "a1", "c", "text")
    wm.save_artifact("ws2", "o", "a2", "c", "text")
    items, total = wm.search_items(workspace_id="ws1")
    assert total == 1
    assert items[0]["workspace_id"] == "ws1"
@pytest.mark.asyncio
async def test_search_invalid_sort_defaults(seeded_runtime):
    resp = await _search({"sort_by": "invalid", "order": "invalid"})
    data = resp.json()
    assert data["total"] == 6
    assert len(data["items"]) == 6