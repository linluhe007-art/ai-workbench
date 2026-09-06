"""
ResearchAgent - Phase Beta-Search Upgrade

Information collection agent with real search engine integration.
Responsible for searching, collecting, and structuring information.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentType, AgentStatus
from app.search.search_engine import get_search_engine, SearchResult
from app.research.extractor import get_extractor, Document
from app.research.citation import get_citation_manager, Citation
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResearchResult:
    """Structured research result."""
    query: str
    sources: list[dict] = field(default_factory=list)
    extracted_documents: list[dict] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    source_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "sources": self.sources,
            "extracted_documents": self.extracted_documents,
            "citations": self.citations,
            "source_count": self.source_count,
            "created_at": self.created_at,
        }


class ResearchAgent(BaseAgent):
    """Information collection Agent with search engine integration."""

    def __init__(self, llm_provider=None):
        self._llm = llm_provider
        config = AgentConfig(
            id="research",
            name="research",
            type=AgentType.RESEARCH,
            capabilities=["web_search", "information_extract", "source_collect", "rss_parse", "news_crawl"],
            extra={"description": "Search and collect information from the web"},
        )
        super().__init__(config)
        self._status = AgentStatus.ONLINE

    async def chat(self, message: str, context: dict | None = None) -> str:
        return f"[ResearchAgent] Received query: {message}"

    async def execute_task(self, task_input: dict) -> AgentResponse:
        """
        Execute research task.
        Input: {"task": str, "query": str, "max_sources": int, "context": dict}
        Output: AgentResponse with ResearchResult in data
        """
        task = task_input.get("task", "")
        query = task_input.get("query", task)
        max_sources = task_input.get("max_sources", 10)

        start = time.monotonic()
        engine = get_search_engine()
        extractor = get_extractor()
        citation_mgr = get_citation_manager()

        # Search
        search_response = await engine.search(query, max_results=max_sources)
        sources = []
        citations = []

        for sr in search_response.results:
            source_dict = sr.to_dict()
            sources.append(source_dict)
            cit = Citation(url=sr.url, title=sr.title, source_type="web")
            citations.append(cit)

        # Extract content from results
        documents = []
        for sr in search_response.results:
            doc = extractor.extract(sr.snippet + "\n" + sr.content, sr.url, "html")
            documents.append(doc.to_dict())

        # Record citations
        task_id = task_input.get("task_id", "")
        if task_id:
            citation_mgr.record_batch(task_id, citations)

        result = ResearchResult(
            query=query,
            sources=sources,
            extracted_documents=documents,
            citations=[c.to_dict() for c in citations],
            source_count=len(sources),
        )

        llm_summary = await self._summarize_with_llm(query, sources)
        summary = llm_summary or f"Collected {len(sources)} sources for '{query}'"

        duration = int((time.monotonic() - start) * 1000)

        return AgentResponse(
            success=True,
            data={
                "agent": "research",
                "research_result": result.to_dict(),
                "source_mode": search_response.source_mode,
                "query": query,
                "summary": summary,
                "llm_summary": llm_summary or "",
            },
            agent_id=self.id,
            duration_ms=duration,
            metadata={
                "source_mode": search_response.source_mode,
                "provider": search_response.provider,
                "llm_used": bool(llm_summary),
            },
        )

    def get_capabilities(self) -> list[str]:
        caps = super().get_capabilities()
        if not caps:
            caps = ["web_search", "information_extract", "source_collect", "rss_parse", "news_crawl"]
        return caps
