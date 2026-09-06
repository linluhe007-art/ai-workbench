"""
Phase 4.22 tests - Agent Lifecycle API
Covers: GET /registry, POST /register, POST /heartbeat, POST /disable, POST /enable, GET /runtime
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


class TestAgentRegistry:
    async def test_get_registry_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/registry")
        assert resp.status_code == 200

    async def test_get_registry_has_agents(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/registry")
        data = resp.json()
        assert "agents" in data
        assert "total" in data
        assert isinstance(data["agents"], list)
        assert data["total"] >= 0


class TestAgentRegister:
    async def test_register_new_agent(self):
        async with _client() as c:
            resp = await c.post("/api/v1/agents/register", json={
                "agent_id": "test-agent-1",
                "capabilities": ["research"],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["agent_id"] == "test-agent-1"

    async def test_register_duplicate(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "dup-agent",
                "capabilities": ["research"],
            })
            resp = await c.post("/api/v1/agents/register", json={
                "agent_id": "dup-agent",
                "capabilities": ["research"],
            })
        data = resp.json()
        assert data["success"] is True
        assert "already registered" in data["message"]

    async def test_register_empty_capabilities(self):
        async with _client() as c:
            resp = await c.post("/api/v1/agents/register", json={
                "agent_id": "no-cap-agent",
                "capabilities": [],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestAgentHeartbeat:
    async def test_heartbeat_existing_agent(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "hb-agent",
                "capabilities": ["research"],
            })
            resp = await c.post("/api/v1/agents/hb-agent/heartbeat")
        assert resp.status_code == 200
        data = resp.json()
        assert data["alive"] is True

    async def test_heartbeat_nonexistent_agent(self):
        async with _client() as c:
            resp = await c.post("/api/v1/agents/ghost-agent/heartbeat")
        assert resp.status_code == 404


class TestAgentDisableEnable:
    async def test_disable_agent(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "toggle-agent",
                "capabilities": ["analysis"],
            })
            resp = await c.post("/api/v1/agents/toggle-agent/disable")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["enabled"] is False

    async def test_enable_agent(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "toggle-agent-2",
                "capabilities": ["analysis"],
            })
            await c.post("/api/v1/agents/toggle-agent-2/disable")
            resp = await c.post("/api/v1/agents/toggle-agent-2/enable")
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is True

    async def test_disable_nonexistent(self):
        async with _client() as c:
            resp = await c.post("/api/v1/agents/ghost/disable")
        assert resp.status_code == 404


class TestAgentRuntime:
    async def test_get_runtime_returns_200(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "runtime-agent",
                "capabilities": ["research"],
            })
            resp = await c.get("/api/v1/agents/runtime-agent/runtime")
        assert resp.status_code == 200

    async def test_get_runtime_has_fields(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "runtime-agent-2",
                "capabilities": ["analysis"],
            })
            resp = await c.get("/api/v1/agents/runtime-agent-2/runtime")
        data = resp.json()
        assert "agent_id" in data
        assert "state" in data
        assert "load" in data

    async def test_get_runtime_nonexistent(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/ghost/runtime")
        assert resp.status_code == 404


class TestSchedulerStatus:
    async def test_scheduler_status_returns_200(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/scheduler/status")
        assert resp.status_code == 200

    async def test_scheduler_status_has_agents_array(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/scheduler/status")
        data = resp.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

class TestAgentRegistryAdvanced:
    async def test_registry_reflects_registration(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "reflect-agent",
                "capabilities": ["writing"],
            })
            resp = await c.get("/api/v1/agents/registry")
        data = resp.json()
        ids = [a["agent_id"] for a in data["agents"]]
        assert "reflect-agent" in ids

    async def test_registry_with_metadata(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "meta-agent",
                "capabilities": ["research"],
                "metadata": {"version": "1.0"},
            })
            resp = await c.get("/api/v1/agents/meta-agent/capabilities")
        assert resp.status_code == 200


class TestSchedulerStatusAdvanced:
    async def test_scheduler_status_includes_registered_agents(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "sched-agent",
                "capabilities": ["analysis"],
            })
            resp = await c.get("/api/v1/agents/scheduler/status")
        ids = [a["agent_id"] for a in resp.json()["agents"]]
        assert "sched-agent" in ids

    async def test_scheduler_status_returns_total(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/scheduler/status")
        data = resp.json()
        assert "total" in data


class TestAgentRuntimeExtended:
    async def test_runtime_has_capabilities(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "cap-runtime",
                "capabilities": ["research", "writing"],
            })
            resp = await c.get("/api/v1/agents/cap-runtime/runtime")
        data = resp.json()
        assert "capabilities" in data

    async def test_runtime_has_load(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "load-agent",
                "capabilities": ["research"],
            })
            resp = await c.get("/api/v1/agents/load-agent/runtime")
        data = resp.json()
        assert "load" in data
        assert "active_tasks" in data["load"]

class TestAgentHeartbeatAdvanced:
    async def test_heartbeat_updates_timestamp(self):
        async with _client() as c:
            await c.post("/api/v1/agents/register", json={
                "agent_id": "ts-agent",
                "capabilities": ["research"],
            })
            resp = await c.post("/api/v1/agents/ts-agent/heartbeat")
        data = resp.json()
        assert "timestamp" in data
        assert data["alive"] is True


class TestAgentRegisterEdgeCases:
    async def test_register_long_capabilities_list(self):
        caps = ["research", "analysis", "writing", "coding", "testing"]
        async with _client() as c:
            resp = await c.post("/api/v1/agents/register", json={
                "agent_id": "multi-cap",
                "capabilities": caps,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["capabilities"] == caps

    async def test_register_without_capabilities_field(self):
        async with _client() as c:
            resp = await c.post("/api/v1/agents/register", json={
                "agent_id": "no-caps",
            })
        assert resp.status_code == 200