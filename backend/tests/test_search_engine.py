"""Phase Beta-Search tests - Search Engine"""
import pytest
from app.search.search_engine import (
    SearchEngine, SearchResult, SearchResponse, SearchProviderType,
    MockSearchProvider, get_search_engine,
)


class TestSearchResult:
    def test_create_basic(self):
        sr = SearchResult(title="Test", url="https://example.com")
        assert sr.title == "Test"
        assert sr.url == "https://example.com"
        assert sr.snippet == ""

    def test_to_dict(self):
        sr = SearchResult(title="T", url="https://x.com", snippet="S", relevance_score=0.9)
        d = sr.to_dict()
        assert d["title"] == "T"
        assert d["url"] == "https://x.com"
        assert d["relevance_score"] == 0.9

    def test_default_values(self):
        sr = SearchResult(title="", url="")
        assert sr.source == ""
        assert sr.published == ""
        assert sr.relevance_score == 0.0

    def test_metadata(self):
        sr = SearchResult(title="T", url="U", metadata={"key": "val"})
        assert sr.metadata["key"] == "val"
        assert sr.to_dict()["metadata"]["key"] == "val"


class TestSearchResponse:
    def test_create(self):
        resp = SearchResponse(query="test")
        assert resp.query == "test"
        assert resp.results == []
        assert resp.source_mode == "live"

    def test_to_dict_with_results(self):
        sr = SearchResult(title="R1", url="https://r1.com")
        resp = SearchResponse(query="q", results=[sr])
        d = resp.to_dict()
        assert len(d["results"]) == 1
        assert d["results"][0]["title"] == "R1"

    def test_error_state(self):
        resp = SearchResponse(query="q", error="Timeout", source_mode="llm_only")
        assert resp.error == "Timeout"
        assert resp.source_mode == "llm_only"


class TestMockSearchProvider:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        provider = MockSearchProvider()
        results = await provider.search("AI trends")
        assert len(results) > 0
        assert len(results) <= 10

    @pytest.mark.asyncio
    async def test_search_max_results(self):
        provider = MockSearchProvider()
        results = await provider.search("test", max_results=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_results_have_urls(self):
        provider = MockSearchProvider()
        results = await provider.search("anything")
        for r in results:
            assert r.url.startswith("https://")

    @pytest.mark.asyncio
    async def test_results_have_scores(self):
        provider = MockSearchProvider()
        results = await provider.search("test")
        for r in results:
            assert 0 < r.relevance_score <= 1


class TestSearchEngine:
    @pytest.mark.asyncio
    async def test_search_with_mock(self):
        engine = SearchEngine(provider=MockSearchProvider())
        resp = await engine.search("AI market")
        assert len(resp.results) > 0
        assert resp.query == "AI market"

    @pytest.mark.asyncio
    async def test_source_mode_live(self):
        engine = SearchEngine(provider=MockSearchProvider())
        resp = await engine.search("test")
        assert resp.source_mode == "live"

    @pytest.mark.asyncio
    async def test_duration_recorded(self):
        engine = SearchEngine(provider=MockSearchProvider())
        resp = await engine.search("test")
        assert resp.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_response_to_dict(self):
        engine = SearchEngine(provider=MockSearchProvider())
        resp = await engine.search("q")
        d = resp.to_dict()
        assert "query" in d
        assert "results" in d
        assert "source_mode" in d

    @pytest.mark.asyncio
    async def test_set_provider(self):
        engine = SearchEngine(provider=MockSearchProvider())
        engine.set_provider(MockSearchProvider())
        resp = await engine.search("test")
        assert len(resp.results) > 0


class TestSearchProviderType:
    def test_values(self):
        assert SearchProviderType.TAVILY == "tavily"
        assert SearchProviderType.BING == "bing"
        assert SearchProviderType.MOCK == "mock"
        assert SearchProviderType.DUCKDUCKGO == "duckduckgo"

    def test_all_defined(self):
        types = [t.value for t in SearchProviderType]
        assert "mock" in types
        assert "tavily" in types
        assert "bing" in types


class TestSingleton:
    def test_get_search_engine_returns_same(self):
        e1 = get_search_engine()
        e2 = get_search_engine()
        assert e1 is e2
