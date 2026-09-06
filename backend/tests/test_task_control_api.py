"""Phase 4.11 - Task Control API Tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.runtime.manager import get_runtime, reset_runtime, TaskStatus


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    yield
    reset_runtime()


@pytest.mark.asyncio
async def test_create_task_with_timeout():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/tasks", json={"task": "test", "timeout_seconds": 60})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] in ("pending", "queued")


@pytest.mark.asyncio
async def test_cancel_nonexistent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/tasks/nope/cancel")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pause_nonexistent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/tasks/nope/pause")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_resume_nonexistent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/tasks/nope/resume")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retry_nonexistent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/tasks/nope/retry")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_queue_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/queue/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "max_concurrent" in data
    assert "running" in data
    assert "queued" in data


@pytest.mark.asyncio
async def test_cancel_completed_task():
    runtime = get_runtime()
    record = runtime.create_task("t")
    record.status = TaskStatus.COMPLETED
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/tasks/{record.task_id}/cancel")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_pause_completed_task():
    runtime = get_runtime()
    record = runtime.create_task("t")
    record.status = TaskStatus.COMPLETED
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/tasks/{record.task_id}/pause")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_resume_completed_task():
    runtime = get_runtime()
    record = runtime.create_task("t")
    record.status = TaskStatus.COMPLETED
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/tasks/{record.task_id}/resume")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_retry_failed_task():
    runtime = get_runtime()
    record = runtime.create_task("t")
    record.status = TaskStatus.FAILED
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/tasks/{record.task_id}/retry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_retry_cancelled_task():
    runtime = get_runtime()
    record = runtime.create_task("t")
    record.status = TaskStatus.CANCELLED
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/tasks/{record.task_id}/retry")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_retry_timeout_task():
    runtime = get_runtime()
    record = runtime.create_task("t")
    record.status = TaskStatus.TIMEOUT
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/v1/tasks/{record.task_id}/retry")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_task_list_includes_new_fields():
    runtime = get_runtime()
    record = runtime.create_task("test task")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks")
    data = resp.json()
    assert len(data["tasks"]) == 1
    task = data["tasks"][0]
    assert "attempt" in task
    assert "max_iterations" in task


@pytest.mark.asyncio
async def test_task_detail_includes_new_fields():
    runtime = get_runtime()
    record = runtime.create_task("test")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/tasks/{record.task_id}")
    data = resp.json()
    assert data["attempt"] == 0
    assert data["max_iterations"] == 3