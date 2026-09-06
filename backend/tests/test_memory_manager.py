"""
Phase 5.3 tests - MemoryManager, MemoryType, Long-term Memory API.
Tests: save, search, update, forget, type filtering, importance, tags, stats, API endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.memory.manager import MemoryManager, MemoryRecord, MemoryType, get_memory_manager, reset_memory_manager
from app.main import app


@pytest.fixture(autouse=True)
def _reset():
    reset_memory_manager()
    yield
    reset_memory_manager()


# ==========================================================================
# MemoryType Enum Tests
# ==========================================================================

class TestMemoryType:
    def test_all_types_exist(self):
        types = [t.value for t in MemoryType]
        assert "profile" in types
        assert "preference" in types
        assert "project" in types
        assert "knowledge" in types
        assert "experience" in types

    def test_type_from_string(self):
        assert MemoryType("profile") == MemoryType.PROFILE
        assert MemoryType("knowledge") == MemoryType.KNOWLEDGE

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError):
            MemoryType("invalid")


# ==========================================================================
# MemoryRecord Tests
# ==========================================================================

class TestMemoryRecord:
    def test_record_defaults(self):
        r = MemoryRecord(content="test")
        assert r.content == "test"
        assert r.importance == 0.5
        assert r.memory_type == MemoryType.KNOWLEDGE
        assert r.tags == []

    def test_record_to_dict(self):
        r = MemoryRecord(content="hello", memory_type=MemoryType.PROFILE, importance=0.8, tags=["tag1"])
        d = r.to_dict()
        assert d["content"] == "hello"
        assert d["memory_type"] == "profile"
        assert d["importance"] == 0.8
        assert d["tags"] == ["tag1"]

    def test_record_has_id(self):
        r = MemoryRecord(content="test")
        assert r.id
        assert len(r.id) > 0

    def test_record_has_timestamps(self):
        r = MemoryRecord(content="test")
        assert r.created_at
        assert r.updated_at


# ==========================================================================
# MemoryManager save_memory Tests
# ==========================================================================

class TestSaveMemory:
    def test_save_basic(self):
        mgr = MemoryManager()
        record = mgr.save_memory("hello world")
        assert record.content == "hello world"
        assert record.memory_type == MemoryType.KNOWLEDGE

    def test_save_with_type(self):
        mgr = MemoryManager()
        record = mgr.save_memory("my name is John", memory_type="profile")
        assert record.memory_type == MemoryType.PROFILE

    def test_save_with_tags(self):
        mgr = MemoryManager()
        record = mgr.save_memory("AI research", tags=["ai", "research"])
        assert "ai" in record.tags
        assert "research" in record.tags

    def test_save_with_importance(self):
        mgr = MemoryManager()
        record = mgr.save_memory("important", importance=0.9)
        assert record.importance == 0.9

    def test_save_clamps_importance_high(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test", importance=1.5)
        assert record.importance == 1.0

    def test_save_clamps_importance_low(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test", importance=-0.5)
        assert record.importance == 0.0

    def test_save_all_types(self):
        mgr = MemoryManager()
        for t in MemoryType:
            record = mgr.save_memory(f"test {t.value}", memory_type=t)
            assert record.memory_type == t

    def test_save_with_metadata(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test", metadata={"source": "cli", "version": 1})
        assert record.metadata["source"] == "cli"

    def test_save_multiple(self):
        mgr = MemoryManager()
        mgr.save_memory("one")
        mgr.save_memory("two")
        mgr.save_memory("three")
        assert mgr.get_stats()["total_memories"] == 3


# ==========================================================================
# MemoryManager search_memory Tests
# ==========================================================================

class TestSearchMemory:
    def test_search_by_query(self):
        mgr = MemoryManager()
        mgr.save_memory("artificial intelligence research")
        mgr.save_memory("machine learning basics")
        mgr.save_memory("cooking recipes")
        results = mgr.search_memory(query="intelligence")
        assert len(results) == 1
        assert "artificial" in results[0]["content"]

    def test_search_by_type(self):
        mgr = MemoryManager()
        mgr.save_memory("profile info", memory_type="profile")
        mgr.save_memory("knowledge info", memory_type="knowledge")
        results = mgr.search_memory(memory_type="profile")
        assert len(results) == 1
        assert results[0]["memory_type"] == "profile"

    def test_search_by_tags(self):
        mgr = MemoryManager()
        mgr.save_memory("item1", tags=["python", "coding"])
        mgr.save_memory("item2", tags=["python", "testing"])
        mgr.save_memory("item3", tags=["rust", "coding"])
        results = mgr.search_memory(tags=["python"])
        assert len(results) == 2

    def test_search_multi_tag_intersection(self):
        mgr = MemoryManager()
        mgr.save_memory("item1", tags=["python", "coding"])
        mgr.save_memory("item2", tags=["python"])
        results = mgr.search_memory(tags=["python", "coding"])
        assert len(results) == 1

    def test_search_importance_filter(self):
        mgr = MemoryManager()
        mgr.save_memory("low", importance=0.1)
        mgr.save_memory("high", importance=0.9)
        results = mgr.search_memory(min_importance=0.5)
        assert len(results) == 1
        assert results[0]["content"] == "high"

    def test_search_limit(self):
        mgr = MemoryManager()
        for i in range(20):
            mgr.save_memory(f"item {i}")
        results = mgr.search_memory(limit=5)
        assert len(results) == 5

    def test_search_empty_result(self):
        mgr = MemoryManager()
        mgr.save_memory("test")
        results = mgr.search_memory(query="nonexistent")
        assert results == []

    def test_search_combined_filters(self):
        mgr = MemoryManager()
        mgr.save_memory("AI research paper", memory_type="knowledge", tags=["ai", "research"], importance=0.9)
        mgr.save_memory("AI project plan", memory_type="project", tags=["ai", "planning"], importance=0.7)
        mgr.save_memory("cooking recipe", memory_type="knowledge", tags=["cooking"], importance=0.3)
        results = mgr.search_memory(query="AI", memory_type="knowledge", tags=["ai"], min_importance=0.5)
        assert len(results) == 1
        assert "research" in results[0]["content"]

    def test_search_case_insensitive(self):
        mgr = MemoryManager()
        mgr.save_memory("Artificial Intelligence")
        results = mgr.search_memory(query="artificial")
        assert len(results) == 1
        results2 = mgr.search_memory(query="ARTIFICIAL")
        assert len(results2) == 1


# ==========================================================================
# MemoryManager update_memory Tests
# ==========================================================================

class TestUpdateMemory:
    def test_update_content(self):
        mgr = MemoryManager()
        record = mgr.save_memory("old content")
        result = mgr.update_memory(record.id, content="new content")
        assert result["content"] == "new content"

    def test_update_importance(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test")
        result = mgr.update_memory(record.id, importance=0.99)
        assert result["importance"] == 0.99

    def test_update_tags(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test", tags=["old"])
        result = mgr.update_memory(record.id, tags=["new", "updated"])
        assert set(result["tags"]) == {"new", "updated"}

    def test_update_metadata_merge(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test", metadata={"a": 1})
        result = mgr.update_memory(record.id, metadata={"b": 2})
        assert result["metadata"]["a"] == 1
        assert result["metadata"]["b"] == 2

    def test_update_nonexistent(self):
        mgr = MemoryManager()
        result = mgr.update_memory("nonexistent", content="x")
        assert result is None

    def test_update_reflected_in_search(self):
        mgr = MemoryManager()
        record = mgr.save_memory("old")
        mgr.update_memory(record.id, content="updated content")
        results = mgr.search_memory(query="updated")
        assert len(results) == 1


# ==========================================================================
# MemoryManager forget_memory Tests
# ==========================================================================

class TestForgetMemory:
    def test_forget_removes(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test")
        assert mgr.forget_memory(record.id) is True
        assert mgr.get_memory(record.id) is None
        assert mgr.get_stats()["total_memories"] == 0

    def test_forget_nonexistent(self):
        mgr = MemoryManager()
        assert mgr.forget_memory("nonexistent") is False

    def test_forget_cleans_type_index(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test", memory_type="profile")
        mgr.forget_memory(record.id)
        results = mgr.get_by_type("profile")
        assert results == []

    def test_forget_cleans_tag_index(self):
        mgr = MemoryManager()
        record = mgr.save_memory("test", tags=["python"])
        mgr.forget_memory(record.id)
        results = mgr.search_memory(tags=["python"])
        assert results == []


# ==========================================================================
# MemoryManager type-specific helpers Tests
# ==========================================================================

class TestTypeHelpers:
    def test_get_profile(self):
        mgr = MemoryManager()
        mgr.save_memory("profile data", memory_type="profile")
        results = mgr.get_profile()
        assert len(results) == 1

    def test_get_preferences(self):
        mgr = MemoryManager()
        mgr.save_memory("pref data", memory_type="preference")
        results = mgr.get_preferences()
        assert len(results) == 1

    def test_get_projects(self):
        mgr = MemoryManager()
        mgr.save_memory("project data", memory_type="project")
        results = mgr.get_projects()
        assert len(results) == 1

    def test_get_knowledge(self):
        mgr = MemoryManager()
        mgr.save_memory("knowledge data", memory_type="knowledge")
        results = mgr.get_knowledge()
        assert len(results) == 1

    def test_get_experiences(self):
        mgr = MemoryManager()
        mgr.save_memory("exp data", memory_type="experience")
        results = mgr.get_experiences()
        assert len(results) == 1

    def test_get_high_importance(self):
        mgr = MemoryManager()
        mgr.save_memory("low", importance=0.2)
        mgr.save_memory("high", importance=0.9)
        results = mgr.get_high_importance(threshold=0.5)
        assert len(results) == 1

    def test_get_by_type(self):
        mgr = MemoryManager()
        mgr.save_memory("a", memory_type="knowledge")
        mgr.save_memory("b", memory_type="knowledge")
        results = mgr.get_by_type("knowledge")
        assert len(results) == 2


# ==========================================================================
# MemoryManager stats Tests
# ==========================================================================

class TestMemoryStats:
    def test_empty_stats(self):
        mgr = MemoryManager()
        stats = mgr.get_stats()
        assert stats["total_memories"] == 0

    def test_stats_with_data(self):
        mgr = MemoryManager()
        mgr.save_memory("a", memory_type="profile")
        mgr.save_memory("b", memory_type="knowledge")
        mgr.save_memory("c", memory_type="knowledge")
        stats = mgr.get_stats()
        assert stats["total_memories"] == 3
        assert stats["by_type"]["profile"] == 1
        assert stats["by_type"]["knowledge"] == 2

    def test_stats_tags(self):
        mgr = MemoryManager()
        mgr.save_memory("a", tags=["tag1", "tag2"])
        mgr.save_memory("b", tags=["tag1"])
        stats = mgr.get_stats()
        assert stats["total_tags"] == 2


# ==========================================================================
# API Tests (memory ltm endpoints)
# ==========================================================================

def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestMemoryAPI:
    async def test_save_memory_api(self):
        async with _client() as c:
            resp = await c.post("/api/v1/memory/ltm", json={
                "content": "test memory", "memory_type": "knowledge"
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["content"] == "test memory"

    async def test_save_bad_type(self):
        async with _client() as c:
            resp = await c.post("/api/v1/memory/ltm", json={
                "content": "test", "memory_type": "invalid"
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    async def test_search_api(self):
        async with _client() as c:
            await c.post("/api/v1/memory/ltm", json={"content": "AI research", "tags": ["ai"]})
            resp = await c.post("/api/v1/memory/ltm/search", json={"query": "AI"})
        data = resp.json()
        assert data["success"] is True
        assert data["total"] >= 1

    async def test_get_by_id(self):
        async with _client() as c:
            save_resp = await c.post("/api/v1/memory/ltm", json={"content": "findme"})
            mid = save_resp.json()["data"]["id"]
            resp = await c.get(f"/api/v1/memory/ltm/{mid}")
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["content"] == "findme"

    async def test_get_nonexistent(self):
        async with _client() as c:
            resp = await c.get("/api/v1/memory/ltm/nonexistent")
        data = resp.json()
        assert data["success"] is False

    async def test_update_api(self):
        async with _client() as c:
            save_resp = await c.post("/api/v1/memory/ltm", json={"content": "old"})
            mid = save_resp.json()["data"]["id"]
            resp = await c.put(f"/api/v1/memory/ltm/{mid}", json={"content": "new"})
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["content"] == "new"

    async def test_delete_api(self):
        async with _client() as c:
            save_resp = await c.post("/api/v1/memory/ltm", json={"content": "temp"})
            mid = save_resp.json()["data"]["id"]
            resp = await c.delete(f"/api/v1/memory/ltm/{mid}")
        assert resp.json()["success"] is True

    async def test_delete_nonexistent(self):
        async with _client() as c:
            resp = await c.delete("/api/v1/memory/ltm/nonexistent")
        assert resp.json()["success"] is False

    async def test_ltm_stats_api(self):
        async with _client() as c:
            resp = await c.get("/api/v1/memory/ltm/stats")
        data = resp.json()
        assert data["success"] is True
        assert "data" in data

    async def test_get_by_type_api(self):
        async with _client() as c:
            await c.post("/api/v1/memory/ltm", json={"content": "p", "memory_type": "profile"})
            resp = await c.get("/api/v1/memory/ltm/types/profile")
        data = resp.json()
        assert data["success"] is True

    async def test_invalid_type_api(self):
        async with _client() as c:
            resp = await c.get("/api/v1/memory/ltm/types/badtype")
        data = resp.json()
        assert data["success"] is False

    async def test_profile_api(self):
        async with _client() as c:
            await c.post("/api/v1/memory/ltm", json={"content": "name: John", "memory_type": "profile"})
            resp = await c.get("/api/v1/memory/ltm/profile")
        data = resp.json()
        assert data["success"] is True

    async def test_preferences_api(self):
        async with _client() as c:
            await c.post("/api/v1/memory/ltm", json={"content": "dark mode", "memory_type": "preference"})
            resp = await c.get("/api/v1/memory/ltm/preferences")
        data = resp.json()
        assert data["success"] is True

    async def test_search_with_type_api(self):
        async with _client() as c:
            await c.post("/api/v1/memory/ltm", json={"content": "knowledge", "memory_type": "knowledge"})
            await c.post("/api/v1/memory/ltm", json={"content": "experience", "memory_type": "experience"})
            resp = await c.post("/api/v1/memory/ltm/search", json={"memory_type": "knowledge"})
        data = resp.json()
        assert data["total"] == 1

    async def test_search_with_tags_api(self):
        async with _client() as c:
            await c.post("/api/v1/memory/ltm", json={"content": "test", "tags": ["python"]})
            resp = await c.post("/api/v1/memory/ltm/search", json={"tags": ["python"]})
        data = resp.json()
        assert data["total"] >= 1


# ==========================================================================
# Singleton Tests
# ==========================================================================

class TestSingleton:
    def test_get_memory_manager_returns_same(self):
        reset_memory_manager()
        mgr1 = get_memory_manager()
        mgr2 = get_memory_manager()
        assert mgr1 is mgr2

    def test_reset_creates_new(self):
        reset_memory_manager()
        mgr1 = get_memory_manager()
        reset_memory_manager()
        mgr2 = get_memory_manager()
        assert mgr1 is not mgr2

    def test_get_memory_manager_with_user(self):
        reset_memory_manager()
        mgr = get_memory_manager(user_id="user123")
        mgr.save_memory("test")
        stats = mgr.get_stats()
        assert stats["user_id"] == "user123"
