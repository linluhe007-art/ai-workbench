"""Phase Beta-Search tests - Research API"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestResearchAPI:
    @pytest.mark.asyncio
    async def test_start_research_200(self, client):
        resp = await client.post("/api/v1/research", json={"query": "AI trends"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_start_research_returns_task_id(self, client):
        resp = await client.post("/api/v1/research", json={"query": "test"})
        data = resp.json()
        assert data["success"] is True
        assert "task_id" in data
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_start_research_returns_source_count(self, client):
        resp = await client.post("/api/v1/research", json={"query": "AI", "max_sources": 5})
        data = resp.json()
        assert data["source_count"] > 0

    @pytest.mark.asyncio
    async def test_start_research_with_type(self, client):
        resp = await client.post("/api/v1/research", json={
            "query": "Market analysis",
            "output_type": "analysis",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_sources_200(self, client):
        # First create a research
        create_resp = await client.post("/api/v1/research", json={"query": "test sources"})
        task_id = create_resp.json()["task_id"]

        resp = await client.get(f"/api/v1/research/{task_id}/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "sources" in data

    @pytest.mark.asyncio
    async def test_get_sources_not_found(self, client):
        resp = await client.get("/api/v1/research/nonexistent/sources")
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_get_result_200(self, client):
        create_resp = await client.post("/api/v1/research", json={"query": "test result"})
        task_id = create_resp.json()["task_id"]

        resp = await client.get(f"/api/v1/research/{task_id}/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "artifact" in data

    @pytest.mark.asyncio
    async def test_get_result_not_found(self, client):
        resp = await client.get("/api/v1/research/bad-id/result")
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_start_research_empty_query(self, client):
        resp = await client.post("/api/v1/research", json={"query": ""})
        assert resp.status_code == 200
        data = resp.json()
        # Should still work, just might have fewer results
        assert "task_id" in data

    @pytest.mark.asyncio
    async def test_multiple_research_tasks(self, client):
        r1 = await client.post("/api/v1/research", json={"query": "query 1"})
        r2 = await client.post("/api/v1/research", json={"query": "query 2"})
        assert r1.json()["task_id"] != r2.json()["task_id"]
