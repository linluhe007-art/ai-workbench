"""Phase Beta-Search tests - ResearchAgent"""
import pytest
from app.agents.research_agent import ResearchAgent, ResearchResult


class TestResearchResult:
    def test_create(self):
        rr = ResearchResult(query="test query")
        assert rr.query == "test query"
        assert rr.sources == []
        assert rr.source_count == 0

    def test_to_dict(self):
        rr = ResearchResult(
            query="q",
            sources=[{"title": "T", "url": "https://x.com"}],
            source_count=1,
        )
        d = rr.to_dict()
        assert d["query"] == "q"
        assert d["source_count"] == 1
        assert len(d["sources"]) == 1


class TestResearchAgentExecute:
    @pytest.mark.asyncio
    async def test_execute_task_returns_success(self):
        agent = ResearchAgent()
        resp = await agent.execute_task({"task": "AI trends", "query": "AI trends 2026"})
        assert resp.success is True
        assert resp.agent_id == "research"

    @pytest.mark.asyncio
    async def test_execute_task_has_sources(self):
        agent = ResearchAgent()
        resp = await agent.execute_task({"task": "AI", "query": "AI", "max_sources": 5})
        data = resp.data
        assert "research_result" in data
        result = data["research_result"]
        assert result["source_count"] >= 1

    @pytest.mark.asyncio
    async def test_execute_task_returns_data(self):
        agent = ResearchAgent()
        resp = await agent.execute_task({"task": "test", "query": "test query"})
        assert resp.data["agent"] == "research"
        assert "summary" in resp.data

    @pytest.mark.asyncio
    async def test_execute_task_records_duration(self):
        agent = ResearchAgent()
        resp = await agent.execute_task({"task": "test", "query": "test"})
        assert resp.duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_task_with_max_sources(self):
        agent = ResearchAgent()
        resp = await agent.execute_task({"task": "x", "query": "x", "max_sources": 3})
        result = resp.data["research_result"]
        assert result["source_count"] <= 3

    @pytest.mark.asyncio
    async def test_execute_task_metadata_has_source_mode(self):
        agent = ResearchAgent()
        resp = await agent.execute_task({"task": "test", "query": "test"})
        assert "source_mode" in resp.metadata

    @pytest.mark.asyncio
    async def test_chat_returns_string(self):
        agent = ResearchAgent()
        result = await agent.chat("hello")
        assert "ResearchAgent" in result

    def test_get_capabilities(self):
        agent = ResearchAgent()
        caps = agent.get_capabilities()
        assert "web_search" in caps
        assert "information_extract" in caps
        assert "source_collect" in caps


class TestResearchAgentConfig:
    def test_agent_type(self):
        agent = ResearchAgent()
        from app.agents.base import AgentType
        assert agent.config.type == AgentType.RESEARCH

    def test_agent_id(self):
        agent = ResearchAgent()
        assert agent.id == "research"

    def test_agent_name(self):
        agent = ResearchAgent()
        assert agent.config.name == "research"
