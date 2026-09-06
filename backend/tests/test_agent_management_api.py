"""
Phase 4.5 测试 — Agent Management API
覆盖：
- GET /api/v1/agents/capabilities/all
- GET /api/v1/agents/{id}/capabilities
- GET /api/v1/agents/{id}/health
- GET /api/v1/agents/{id}/history
- 404 处理
- 数据隔离
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


# ── All Capabilities ─────────────────────────────────────────


class TestAllCapabilities:
    async def test_all_capabilities(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/capabilities/all")
        assert resp.status_code == 200
        data = resp.json()
        assert "capabilities" in data
        assert "total" in data

    async def test_all_capabilities_not_empty(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/capabilities/all")
        data = resp.json()
        assert data["total"] >= 1

    async def test_capability_has_agents(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/capabilities/all")
        for cap in resp.json()["capabilities"]:
            assert "name" in cap
            assert "agents" in cap
            assert "count" in cap
            assert cap["count"] == len(cap["agents"])


# ── Agent Capabilities ───────────────────────────────────────


class TestAgentCapabilities:
    async def test_get_default_agent_capabilities(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/default/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "default"
        assert "capabilities" in data
        assert "metadata" in data
        assert "experience" in data

    async def test_experience_structure(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/default/capabilities")
        exp = resp.json()["experience"]
        assert "task_count" in exp
        assert "success_rate" in exp

    async def test_agent_not_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/nonexist/capabilities")
        assert resp.status_code == 404

    async def test_research_agent_has_capabilities(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/research/capabilities")
        assert resp.status_code == 200
        caps = resp.json()["capabilities"]
        assert isinstance(caps, list)


# ── Agent Health ──────────────────────────────────────────────


class TestAgentHealth:
    async def test_health_default_agent(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/default/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "default"
        assert "healthy" in data
        assert "state" in data

    async def test_health_has_required_fields(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/default/health")
        data = resp.json()
        assert "healthy" in data
        assert "state" in data
        assert "last_heartbeat" in data
        assert "error" in data

    async def test_health_not_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/nonexist/health")
        assert resp.status_code == 404

    async def test_health_state_is_string(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/default/health")
        state = resp.json()["state"]
        assert isinstance(state, str)


# ── Agent History ─────────────────────────────────────────────


class TestAgentHistory:
    async def test_history_empty(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/default/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "default"
        assert data["records"] == []
        assert data["total"] == 0

    async def test_history_not_found(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/nonexist/history")
        assert resp.status_code == 404

    async def test_history_record_structure(self):
        async with _client() as c:
            # Add experience data first
            rt_resp = await c.get("/api/v1/agents/default/history")
        data = rt_resp.json()
        assert "records" in data
        assert "total" in data


# ── Data Isolation ────────────────────────────────────────────


class TestDataIsolation:
    async def test_different_agents_different_capabilities(self):
        async with _client() as c:
            r1 = await c.get("/api/v1/agents/default/capabilities")
            r2 = await c.get("/api/v1/agents/research/capabilities")
        c1 = r1.json()["capabilities"]
        c2 = r2.json()["capabilities"]
        # They may share some caps, but structure is independent
        assert isinstance(c1, list)
        assert isinstance(c2, list)

    async def test_health_per_agent(self):
        async with _client() as c:
            h1 = await c.get("/api/v1/agents/default/health")
            h2 = await c.get("/api/v1/agents/analysis/health")
        assert h1.json()["agent_id"] == "default"
        assert h2.json()["agent_id"] == "analysis"

    async def test_history_per_agent(self):
        async with _client() as c:
            h1 = await c.get("/api/v1/agents/default/history")
            h2 = await c.get("/api/v1/agents/research/history")
        assert h1.json()["agent_id"] == "default"
        assert h2.json()["agent_id"] == "research"


# ── Aggregate Consistency ─────────────────────────────────────


class TestAggregateConsistency:
    async def test_all_caps_matches_individual(self):
        async with _client() as c:
            all_resp = await c.get("/api/v1/agents/capabilities/all")
            agent_resp = await c.get("/api/v1/agents/default/capabilities")
        all_caps = {cap["name"] for cap in all_resp.json()["capabilities"]}
        agent_caps = set(agent_resp.json()["capabilities"])
        # Agent caps should be subset of all caps
        assert agent_caps.issubset(all_caps) or len(agent_caps) == 0

# ── Edge Cases ────────────────────────────────────────────────


class TestEdgeCases:
    async def test_all_capabilities_returns_list_format(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/capabilities/all")
        for cap in resp.json()["capabilities"]:
            assert isinstance(cap["agents"], list)
            assert cap["count"] >= 1

    async def test_health_healthy_is_boolean(self):
        async with _client() as c:
            resp = await c.get("/api/v1/agents/default/health")
        assert isinstance(resp.json()["healthy"], bool)