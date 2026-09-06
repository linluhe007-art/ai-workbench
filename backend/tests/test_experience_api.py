"""
Phase 4.23 tests - Experience API
Covers: GET /search, POST /feedback, GET /stats, GET /recommendations
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


def _seed_engine():
    runtime = get_runtime()
    from app.learning.experience_engine import ExperienceEngine
    engine = ExperienceEngine(runtime.experience)
    engine.record_experience("search web", ["researcher"], True, 100)
    engine.record_experience("analyze data", ["analyst"], True, 200)
    engine.record_experience("write report", ["writer"], False, 150, {"error": "timeout"})
    runtime._experience_engine = engine


class TestSearch:
    async def test_search_returns_200(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/search", params={"q": "search"})
        assert resp.status_code == 200

    async def test_search_has_results(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/search", params={"q": "search"})
        data = resp.json()
        assert "results" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_search_empty_query(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/search", params={"q": ""})
        assert resp.status_code == 200

    async def test_search_with_success_filter(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/search", params={"q": "", "success": True})
        data = resp.json()
        for r in data["results"]:
            assert r["success"] is True

    async def test_search_with_failure_filter(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/search", params={"q": "", "success": False})
        data = resp.json()
        for r in data["results"]:
            assert r["success"] is False


class TestFeedback:
    async def test_feedback_success(self):
        async with _client() as c:
            resp = await c.post("/api/v1/experience/feedback", json={
                "task_id": "task-1",
                "task_pattern": "test",
                "rating": 7.5,
                "comment": "good",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["rating"] == 7.5

    async def test_feedback_without_comment(self):
        async with _client() as c:
            resp = await c.post("/api/v1/experience/feedback", json={
                "task_id": "t2",
                "rating": 5.0,
            })
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestStats:
    async def test_stats_returns_200(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/stats")
        assert resp.status_code == 200

    async def test_stats_has_sections(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/stats")
        data = resp.json()
        assert "experience" in data
        assert "feedback" in data

    async def test_stats_experience_fields(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/stats")
        exp = resp.json()["experience"]
        assert "total_records" in exp
        assert "success_rate" in exp
        assert exp["total_records"] >= 3


class TestRecommendations:
    async def test_recommendations_returns_200(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/recommendations", params={"task_pattern": "search"})
        assert resp.status_code == 200

    async def test_recommendations_has_fields(self):
        _seed_engine()
        async with _client() as c:
            resp = await c.get("/api/v1/experience/recommendations", params={"task_pattern": "search"})
        data = resp.json()
        assert "recommended_agents" in data
        assert "historical_success_rate" in data
        assert "warnings" in data

    async def test_recommendations_missing_param(self):
        async with _client() as c:
            resp = await c.get("/api/v1/experience/recommendations")
        assert resp.status_code == 422