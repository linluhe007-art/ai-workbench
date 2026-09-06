"""
Phase 4.25 tests - Cluster API + extended system endpoints
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


class TestClusterAPI:
    async def test_cluster_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        assert resp.status_code == 200

    async def test_cluster_has_instances(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        data = resp.json()
        assert "instances" in data
        assert isinstance(data["instances"], list)

    async def test_cluster_has_total(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        data = resp.json()
        assert "total" in data
        assert data["total"] >= 0

    async def test_cluster_has_self(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        data = resp.json()
        assert "self" in data

    async def test_cluster_has_leader_field(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        data = resp.json()
        assert "leader" in data

    async def test_cluster_has_health(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        data = resp.json()
        assert "health" in data
        assert "persistence" in data["health"]
        assert "redis" in data["health"]

    async def test_cluster_has_timestamp(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        data = resp.json()
        assert "timestamp" in data

    async def test_cluster_self_in_instances(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        data = resp.json()
        ids = [i["instance_id"] for i in data["instances"]]
        assert data["self"] in ids


class TestHealthAPI:
    async def test_health_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/health")
        assert resp.status_code == 200

    async def test_health_status_healthy(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/health")
        assert resp.json()["status"] == "healthy"


class TestReadinessAPI:
    async def test_readiness_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/readiness")
        assert resp.status_code == 200

    async def test_readiness_has_ready_field(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/readiness")
        assert "ready" in resp.json()


class TestInfoAPI:
    async def test_info_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/info")
        assert resp.status_code == 200

    async def test_info_has_instance_id(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/info")
        assert "instance_id" in resp.json()


class TestMetricsAPI:
    async def test_metrics_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/metrics")
        assert resp.status_code == 200

    async def test_metrics_has_queue(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/metrics")
        assert "queue" in resp.json()

class TestClusterAPIEdge:
    async def test_cluster_instance_role_field(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        instances = resp.json()["instances"]
        for inst in instances:
            assert "role" in inst

    async def test_cluster_instance_status_field(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        instances = resp.json()["instances"]
        for inst in instances:
            assert "status" in inst

    async def test_cluster_instance_started_at_field(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        instances = resp.json()["instances"]
        for inst in instances:
            assert "started_at" in inst


class TestSystemAPIEdge:
    async def test_health_has_service_field(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/health")
        assert resp.json()["service"] == "ai-workbench"

    async def test_health_has_timestamp(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/health")
        assert "timestamp" in resp.json()

    async def test_readiness_has_status(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/readiness")
        assert "status" in resp.json()

    async def test_info_has_status(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/info")
        assert "status" in resp.json()

    async def test_metrics_returns_dict(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/metrics")
        assert isinstance(resp.json(), dict)

class TestSystemAPIShutdown:
    async def test_shutdown_endpoint_exists(self):
        async with _client() as c:
            resp = await c.post("/api/v1/system/shutdown")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestClusterAPIMultiCall:
    async def test_cluster_consistent_calls(self):
        async with _client() as c:
            r1 = await c.get("/api/v1/system/cluster")
            r2 = await c.get("/api/v1/system/cluster")
        assert r1.status_code == 200
        assert r2.status_code == 200

class TestClusterAPIMore:
    async def test_cluster_always_returns_dict(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        assert isinstance(resp.json(), dict)

    async def test_cluster_instances_are_objects(self):
        async with _client() as c:
            resp = await c.get("/api/v1/system/cluster")
        instances = resp.json()["instances"]
        for inst in instances:
            assert isinstance(inst, dict)