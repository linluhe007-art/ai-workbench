"""
Phase 4.23 tests - ExperienceRetrieval
Covers: search, filter, find_similar, embedding placeholder
"""
import pytest

from app.memory.experience import ExperienceMemory
from app.learning.retrieval import ExperienceRetrieval, ExperienceSearchResult


@pytest.fixture
def retrieval():
    mem = ExperienceMemory()
    # Seed data
    mem.record_experience("search web for AI news", ["researcher"], True, {"source": "web"})
    mem.record_experience("analyze market data", ["analyst"], True, {"source": "csv"})
    mem.record_experience("write report on findings", ["writer"], True, {"format": "md"})
    mem.record_experience("search web for trends", ["researcher"], False, {"error": "timeout"})
    mem.record_experience("analyze sales data", ["analyst", "researcher"], True, {"source": "db"})
    return ExperienceRetrieval(mem)


class TestExperienceRetrievalSearch:
    def test_search_all(self, retrieval):
        results = retrieval.search()
        assert len(results) >= 5

    def test_search_with_query(self, retrieval):
        results = retrieval.search(query="search web")
        assert len(results) >= 1
        assert any("search" in r.task_pattern for r in results)

    def test_search_filter_success(self, retrieval):
        results = retrieval.search(filter_success=True)
        assert all(r.success for r in results)

    def test_search_filter_failures(self, retrieval):
        results = retrieval.search(filter_success=False)
        assert all(not r.success for r in results)

    def test_search_filter_agents(self, retrieval):
        results = retrieval.search(filter_agents=["analyst"])
        assert len(results) >= 1
        assert all("analyst" in r.agents for r in results)

    def test_search_min_score(self, retrieval):
        results = retrieval.search(query="search web", min_score=0.5)
        assert all(r.score >= 0.5 for r in results)

    def test_search_limit(self, retrieval):
        results = retrieval.search(limit=2)
        assert len(results) <= 2


class TestExperienceRetrievalSimilar:
    def test_find_similar(self, retrieval):
        results = retrieval.find_similar("search web")
        assert len(results) >= 1
        assert "search" in results[0].task_pattern.lower()

    def test_find_similar_no_match(self, retrieval):
        results = retrieval.find_similar("quantum physics")
        assert results == []


class TestExperienceRetrievalEmbedding:
    def test_embedding_placeholder(self, retrieval):
        vec = retrieval.get_embedding_placeholder("test text")
        assert len(vec) == 8
        assert all(isinstance(v, float) for v in vec)

    def test_embedding_empty_text(self, retrieval):
        vec = retrieval.get_embedding_placeholder("")
        assert len(vec) == 8

    def test_embedding_different_texts(self, retrieval):
        v1 = retrieval.get_embedding_placeholder("hello")
        v2 = retrieval.get_embedding_placeholder("world")
        # Should produce different vectors
        assert v1 != v2


class TestExperienceSearchResult:
    def test_result_fields(self):
        r = ExperienceSearchResult(
            task_pattern="test",
            score=0.95,
            agents=["a1"],
            success=True,
            created_at="2026-01-01T00:00:00",
        )
        assert r.task_pattern == "test"
        assert r.score == 0.95
        assert r.agents == ["a1"]
        assert r.success is True

    def test_result_defaults(self):
        r = ExperienceSearchResult(task_pattern="test", score=0.5)
        assert r.agents == []
        assert r.success is False
        assert r.created_at == ""
        assert r.metadata == {}