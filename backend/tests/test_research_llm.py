"""Tests for LLM integration in the ResearchAgent."""

import pytest

from app.agents.research_agent import ResearchAgent
from app.llm.models import LLMResponse


class FakeProvider:
    def __init__(self, content="LLM summary content"):
        self.content = content
        self.calls = []

    async def generate(self, messages, model=None, temperature=0.2, max_tokens=4000, **kwargs):
        self.calls.append({"messages": messages, "model": model})
        return LLMResponse(content=self.content, model="fake")


class FailingProvider:
    async def generate(self, messages, model=None, temperature=0.2, max_tokens=4000, **kwargs):
        raise RuntimeError("llm failed")


class TestResearchAgentLLM:
    @pytest.mark.asyncio
    async def test_llm_summary_used(self):
        agent = ResearchAgent(llm_provider=FakeProvider("LLM summary content"))
        response = await agent.execute_task({"task": "AI trends", "query": "AI trends 2026"})
        assert response.data["llm_summary"] == "LLM summary content"

    @pytest.mark.asyncio
    async def test_llm_used_metadata_true(self):
        agent = ResearchAgent(llm_provider=FakeProvider("summary"))
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert response.metadata["llm_used"] is True

    @pytest.mark.asyncio
    async def test_llm_summary_in_data(self):
        agent = ResearchAgent(llm_provider=FakeProvider("summary"))
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert response.data["summary"] == "summary"

    @pytest.mark.asyncio
    async def test_provider_receives_prompt(self):
        provider = FakeProvider("summary")
        agent = ResearchAgent(llm_provider=provider)
        await agent.execute_task({"task": "AI trends", "query": "AI trends 2026"})
        assert len(provider.calls) == 1
        messages = provider.calls[0]["messages"]
        assert "AI trends 2026" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back(self):
        agent = ResearchAgent(llm_provider=FailingProvider())
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert response.data["llm_summary"] == ""
        assert response.metadata["llm_used"] is False

    @pytest.mark.asyncio
    async def test_no_provider_no_llm_summary(self):
        agent = ResearchAgent()
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert response.data["llm_summary"] == ""
        assert response.metadata["llm_used"] is False

    @pytest.mark.asyncio
    async def test_no_provider_keeps_default_summary(self):
        agent = ResearchAgent()
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert "Collected" in response.data["summary"]

    @pytest.mark.asyncio
    async def test_source_count_preserved_with_llm(self):
        agent = ResearchAgent(llm_provider=FakeProvider("summary"))
        response = await agent.execute_task({"task": "AI", "query": "AI", "max_sources": 3})
        assert response.data["research_result"]["source_count"] <= 3

    @pytest.mark.asyncio
    async def test_source_mode_preserved_with_llm(self):
        agent = ResearchAgent(llm_provider=FakeProvider("summary"))
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert "source_mode" in response.metadata

    @pytest.mark.asyncio
    async def test_llm_summary_empty_on_empty_content(self):
        agent = ResearchAgent(llm_provider=FakeProvider(""))
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert response.data["llm_summary"] == ""
        assert response.metadata["llm_used"] is False

    def test_default_agent_has_llm_none(self):
        agent = ResearchAgent()
        assert agent._llm is None

    def test_agent_stores_provider(self):
        provider = FakeProvider()
        agent = ResearchAgent(llm_provider=provider)
        assert agent._llm is provider


class TestResearchAgentLLMMore:
    @pytest.mark.asyncio
    async def test_provider_receives_model_none(self):
        provider = FakeProvider("summary")
        await ResearchAgent(llm_provider=provider).execute_task({"task": "AI", "query": "AI"})
        assert provider.calls[0]["model"] is None

    @pytest.mark.asyncio
    async def test_provider_receives_default_temperature(self):
        provider = FakeProvider("summary")
        await ResearchAgent(llm_provider=provider).execute_task({"task": "AI", "query": "AI"})
        assert provider.calls[0]["messages"]

    @pytest.mark.asyncio
    async def test_provider_called_once(self):
        provider = FakeProvider("summary")
        await ResearchAgent(llm_provider=provider).execute_task({"task": "AI", "query": "AI"})
        assert len(provider.calls) == 1

    @pytest.mark.asyncio
    async def test_failure_still_returns_success(self):
        agent = ResearchAgent(llm_provider=FailingProvider())
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert response.success is True

    @pytest.mark.asyncio
    async def test_default_summary_when_no_llm(self):
        response = await ResearchAgent().execute_task({"task": "AI", "query": "AI"})
        assert "Collected" in response.data["summary"]

    @pytest.mark.asyncio
    async def test_llm_summary_not_present_without_llm(self):
        response = await ResearchAgent().execute_task({"task": "AI", "query": "AI"})
        assert response.data["llm_summary"] == ""

    @pytest.mark.asyncio
    async def test_research_result_query_preserved(self):
        response = await ResearchAgent(llm_provider=FakeProvider("summary")).execute_task({"task": "AI", "query": "AI market"})
        assert response.data["research_result"]["query"] == "AI market"

    @pytest.mark.asyncio
    async def test_research_result_sources_preserved(self):
        response = await ResearchAgent(llm_provider=FakeProvider("summary")).execute_task({"task": "AI", "query": "AI", "max_sources": 3})
        assert response.data["research_result"]["source_count"] >= 1

    @pytest.mark.asyncio
    async def test_research_result_citations_preserved(self):
        response = await ResearchAgent(llm_provider=FakeProvider("summary")).execute_task({"task": "AI", "query": "AI"})
        assert "citations" in response.data["research_result"]

    @pytest.mark.asyncio
    async def test_source_mode_present_in_data(self):
        response = await ResearchAgent(llm_provider=FakeProvider("summary")).execute_task({"task": "AI", "query": "AI"})
        assert "source_mode" in response.data

    @pytest.mark.asyncio
    async def test_provider_content_becomes_summary(self):
        agent = ResearchAgent(llm_provider=FakeProvider("custom summary"))
        response = await agent.execute_task({"task": "AI", "query": "AI"})
        assert response.data["summary"] == "custom summary"

    @pytest.mark.asyncio
    async def test_llm_used_true_when_summary(self):
        response = await ResearchAgent(llm_provider=FakeProvider("summary")).execute_task({"task": "AI", "query": "AI"})
        assert response.metadata["llm_used"] is True

    @pytest.mark.asyncio
    async def test_llm_used_false_when_no_provider(self):
        response = await ResearchAgent().execute_task({"task": "AI", "query": "AI"})
        assert response.metadata["llm_used"] is False

