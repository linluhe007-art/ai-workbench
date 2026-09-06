"""
Phase 4.21 tests - Metrics API
Covers: GET /api/v1/metrics, /metrics/tasks, /metrics/agents
        response schema, edge cases
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.runtime.manager import get_runtime, reset_runtime
from app.observability.metrics_collector import get_metrics_collector, reset_metrics_collector


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_metrics_collector()
    yield
    reset_runtime()
    reset_metrics_collector()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestGetMetrics:
    async def test_get_metrics_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        assert resp.status_code == 200

    async def test_get_metrics_has_required_sections(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        data = resp.json()
        assert "cpu" in data
        assert "memory" in data
        assert "runtime" in data
        assert "tasks" in data
        assert "queue" in data
        assert "agents" in data

    async def test_get_metrics_cpu_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        cpu = resp.json()["cpu"]
        assert "percent" in cpu

    async def test_get_metrics_memory_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        mem = resp.json()["memory"]
        assert "total_gb" in mem
        assert "available_gb" in mem
        assert "percent" in mem
        assert "process_mb" in mem

    async def test_get_metrics_runtime_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        rt = resp.json()["runtime"]
        assert "instance_id" in rt
        assert "uptime_seconds" in rt
        assert "status" in rt

    async def test_get_metrics_tasks_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        tasks = resp.json()["tasks"]
        assert "total" in tasks
        assert "created" in tasks
        assert "completed" in tasks
        assert "failed" in tasks
        assert "timeout" in tasks
        assert "cancelled" in tasks

    async def test_get_metrics_queue_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        queue = resp.json()["queue"]
        assert "running" in queue
        assert "queued" in queue
        assert "max_concurrent" in queue

    async def test_get_metrics_agents_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        agents = resp.json()["agents"]
        assert "total_executions" in agents
        assert "success_rate" in agents
        assert "latency" in agents


class TestGetTaskMetrics:
    async def test_get_task_metrics_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics/tasks")
        assert resp.status_code == 200

    async def test_get_task_metrics_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics/tasks")
        data = resp.json()
        assert "total" in data
        assert "completed" in data
        assert "failed" in data
        assert "success_rate" in data
        assert "failure_rate" in data
        assert "average_duration_ms" in data

    async def test_task_metrics_initial_zero(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics/tasks")
        data = resp.json()
        assert data["total"] == 0
        assert data["success_rate"] == 0.0
        assert data["failure_rate"] == 0.0


class TestGetAgentMetrics:
    async def test_get_agent_metrics_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics/agents")
        assert resp.status_code == 200

    async def test_get_agent_metrics_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics/agents")
        data = resp.json()
        assert "total_executions" in data
        assert "agents" in data

    async def test_agent_metrics_returns_array(self):
        async with _client() as c:
            resp = await c.get("/api/v1/metrics/agents")
        data = resp.json()
        assert isinstance(data["agents"], list)


class TestMetricsWithCollectorData:
    async def test_metrics_reflects_counter(self):
        collector = get_metrics_collector()
        collector.increment("tasks_created_total", value=5)
        async with _client() as c:
            resp = await c.get("/api/v1/metrics")
        assert resp.json()["tasks"]["created"] == 5

    async def test_task_metrics_reflects_counters(self):
        collector = get_metrics_collector()
        collector.increment("tasks_created_total", value=10)
        collector.increment("tasks_completed_total", value=7)
        collector.increment("tasks_failed_total", value=2)
        async with _client() as c:
            resp = await c.get("/api/v1/metrics/tasks")
        data = resp.json()
        assert data["total"] == 10
        assert data["completed"] == 7
        assert data["failed"] == 2

    async def test_metrics_success_rate_calculation(self):
        collector = get_metrics_collector()
        collector.increment("tasks_created_total", value=10)
        collector.increment("tasks_completed_total", value=8)
        collector.increment("tasks_failed_total", value=2)
        async with _client() as c:
            resp = await c.get("/api/v1/metrics/tasks")
        data = resp.json()
        assert data["success_rate"] == 0.8
        assert data["failure_rate"] == 0.2