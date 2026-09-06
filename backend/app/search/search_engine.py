"""Search Engine - Phase Beta-Search

Pluggable search infrastructure supporting multiple providers.
Gracefully degrades when search is unavailable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from app.config import get_settings


class SearchProviderType(str, Enum):
    TAVILY = "tavily"
    BING = "bing"
    SERPAPI = "serpapi"
    DUCKDUCKGO = "duckduckgo"
    MOCK = "mock"


@dataclass
class SearchResult:
    """Individual search result item."""
    title: str
    url: str
    snippet: str = ""
    content: str = ""
    source: str = ""
    published: str = ""
    relevance_score: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content,
            "source": self.source,
            "published": self.published,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
        }


@dataclass
class SearchResponse:
    """Aggregated search response."""
    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_results: int = 0
    provider: str = "mock"
    source_mode: str = "live"
    duration_ms: float = 0.0
    error: str = ""
    searched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_results": len(self.results),
            "provider": self.provider,
            "source_mode": self.source_mode,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "searched_at": self.searched_at,
        }


class SearchProvider(Protocol):
    """Protocol for search providers."""

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        ...


class MockSearchProvider:
    """Mock search provider for development and fallback."""

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        results = [
            SearchResult(
                title=f"Understanding {query}: A Comprehensive Guide",
                url=f"https://example.com/guide/{query.replace(' ', '-').lower()}",
                snippet=f"An in-depth exploration of {query}, covering key concepts, trends, and best practices.",
                source="mock-knowledge",
                relevance_score=0.95,
            ),
            SearchResult(
                title=f"Latest Trends in {query} (2026)",
                url=f"https://example.com/trends/{query.replace(' ', '-').lower()}",
                snippet=f"Discover the most recent developments and innovations in {query} for 2026.",
                source="mock-knowledge",
                relevance_score=0.88,
            ),
            SearchResult(
                title=f"Research Report: {query} Market Analysis",
                url=f"https://example.com/report/{query.replace(' ', '-').lower()}",
                snippet=f"Detailed market analysis report covering the landscape of {query}.",
                source="mock-knowledge",
                relevance_score=0.82,
            ),
            SearchResult(
                title=f"Best Practices for {query} Implementation",
                url=f"https://example.com/best-practices/{query.replace(' ', '-').lower()}",
                snippet=f"Practical guidance and proven strategies for effective {query} implementation.",
                source="mock-knowledge",
                relevance_score=0.79,
            ),
            SearchResult(
                title=f"The Future of {query}: Expert Predictions",
                url=f"https://example.com/future/{query.replace(' ', '-').lower()}",
                snippet=f"Leading experts share their predictions and insights on the future of {query}.",
                source="mock-knowledge",
                relevance_score=0.75,
            ),
        ]
        return results[:max_results]


class SearchEngine:
    """Unified search interface with pluggable providers and graceful degradation."""

    def __init__(self, provider: SearchProvider | None = None):
        settings = get_settings()
        self._provider_type = settings.search_provider
        self._api_key = settings.search_api_key
        self._max_results = settings.search_max_results

        self._provider: SearchProvider = provider or self._resolve_provider()
        self._fallback = MockSearchProvider()

    def _resolve_provider(self) -> SearchProvider:
        pt = self._provider_type.lower()
        if pt == SearchProviderType.DUCKDUCKGO:
            from app.search.duckduckgo_provider import DuckDuckGoProvider
            return DuckDuckGoProvider()
        elif pt == SearchProviderType.TAVILY and self._api_key:
            from app.search.tavily_provider import TavilyProvider
            return TavilyProvider(api_key=self._api_key)
        elif pt == SearchProviderType.BING and self._api_key:
            from app.search.bing_provider import BingProvider
            return BingProvider(api_key=self._api_key)
        elif pt == SearchProviderType.SERPAPI and self._api_key:
            from app.search.serpapi_provider import SerpApiProvider
            return SerpApiProvider(api_key=self._api_key)
        else:
            return MockSearchProvider()

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> SearchResponse:
        """Execute search with graceful fallback."""
        import time
        start = time.monotonic()

        try:
            results = await self._provider.search(query, max_results or self._max_results)
            duration = (time.monotonic() - start) * 1000
            return SearchResponse(
                query=query,
                results=results,
                provider=self._provider_type,
                source_mode="live",
                duration_ms=round(duration, 1),
            )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            # Attempt fallback
            try:
                fallback_results = await self._fallback.search(query, max_results or self._max_results)
                return SearchResponse(
                    query=query,
                    results=fallback_results,
                    provider="mock",
                    source_mode="fallback",
                    duration_ms=round(duration, 1),
                    error=str(e),
                )
            except Exception:
                return SearchResponse(
                    query=query,
                    provider="none",
                    source_mode="llm_only",
                    duration_ms=round(duration, 1),
                    error=f"Search unavailable: {e}",
                )

    def set_provider(self, provider: SearchProvider):
        """Replace the current search provider."""
        self._provider = provider


# Singleton
_engine: SearchEngine | None = None


def get_search_engine() -> SearchEngine:
    global _engine
    if _engine is None:
        _engine = SearchEngine()
    return _engine
