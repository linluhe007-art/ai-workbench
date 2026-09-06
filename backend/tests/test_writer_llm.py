"""Tests for LLM integration in the WritingAgent."""

import pytest

from app.agents.writing_agent import WritingAgent
from app.llm.models import LLMResponse


class FakeProvider:
    def __init__(self, content="# LLM generated report"):
        self.content = content
        self.calls = []

    async def generate(self, messages, model=None, temperature=0.2, max_tokens=4000, **kwargs):
        self.calls.append({"messages": messages, "model": model})
        return LLMResponse(content=self.content, model="fake")


class FailingProvider:
    async def generate(self, messages, model=None, temperature=0.2, max_tokens=4000, **kwargs):
        raise RuntimeError("llm failed")


class TestWritingAgentLLM:
    @pytest.mark.asyncio
    async def test_llm_content_used(self):
        agent = WritingAgent(llm_provider=FakeProvider("# LLM generated report"))
        response = await agent.execute_task({
            "task": "AI trends",
            "output_type": "report",
            "research_result": {"sources": [{"title": "S", "url": "https://s.com"}], "source_count": 1},
        })
        assert response.data["content"] == "# LLM generated report"

    @pytest.mark.asyncio
    async def test_llm_used_metadata_true(self):
        agent = WritingAgent(llm_provider=FakeProvider("# LLM generated report"))
        response = await agent.execute_task({
            "task": "AI trends",
            "output_type": "report",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert response.metadata["llm_used"] is True

    @pytest.mark.asyncio
    async def test_provider_receives_prompt(self):
        provider = FakeProvider("# LLM generated report")
        agent = WritingAgent(llm_provider=provider)
        await agent.execute_task({
            "task": "AI trends",
            "output_type": "report",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert len(provider.calls) == 1
        prompt = provider.calls[0]["messages"][0]["content"]
        assert "AI trends" in prompt

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_template(self):
        agent = WritingAgent(llm_provider=FailingProvider())
        response = await agent.execute_task({
            "task": "AI trends",
            "output_type": "report",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert response.metadata["llm_used"] is False
        assert response.data["content"] != ""

    @pytest.mark.asyncio
    async def test_no_provider_uses_template(self):
        agent = WritingAgent()
        response = await agent.execute_task({
            "task": "AI trends",
            "output_type": "report",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert response.metadata["llm_used"] is False
        assert response.data["content"] != ""

    @pytest.mark.asyncio
    async def test_empty_llm_content_falls_back(self):
        agent = WritingAgent(llm_provider=FakeProvider(""))
        response = await agent.execute_task({
            "task": "AI trends",
            "output_type": "report",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert response.metadata["llm_used"] is False
        assert response.data["content"] != ""

    @pytest.mark.asyncio
    async def test_output_type_preserved_with_llm(self):
        agent = WritingAgent(llm_provider=FakeProvider("# content"))
        response = await agent.execute_task({
            "task": "AI trends",
            "output_type": "analysis",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert response.data["output_type"] == "analysis"

    @pytest.mark.asyncio
    async def test_citations_preserved_with_llm(self):
        citations = [{"title": "S", "url": "https://s.com"}]
        agent = WritingAgent(llm_provider=FakeProvider("# content"))
        response = await agent.execute_task({
            "task": "AI trends",
            "output_type": "report",
            "research_result": {"sources": [], "source_count": 0, "citations": citations},
        })
        assert response.data["citations"] == citations

    def test_default_agent_has_llm_none(self):
        agent = WritingAgent()
        assert agent._llm is None

    def test_agent_stores_provider(self):
        provider = FakeProvider()
        agent = WritingAgent(llm_provider=provider)
        assert agent._llm is provider


class TestWritingAgentLLMMore:
    @pytest.mark.asyncio
    async def test_llm_content_article(self):
        agent = WritingAgent(llm_provider=FakeProvider("# article content"))
        response = await agent.execute_task({"task": "T", "output_type": "article", "research_result": {"sources": [], "source_count": 0}})
        assert response.data["content"] == "# article content"

    @pytest.mark.asyncio
    async def test_llm_content_analysis(self):
        agent = WritingAgent(llm_provider=FakeProvider("# analysis content"))
        response = await agent.execute_task({"task": "T", "output_type": "analysis", "research_result": {"sources": [], "source_count": 0}})
        assert response.data["content"] == "# analysis content"

    @pytest.mark.asyncio
    async def test_provider_receives_model_none(self):
        provider = FakeProvider("# content")
        await WritingAgent(llm_provider=provider).execute_task({"task": "T", "output_type": "report", "research_result": {"sources": [], "source_count": 0}})
        assert provider.calls[0]["model"] is None

    @pytest.mark.asyncio
    async def test_provider_called_once(self):
        provider = FakeProvider("# content")
        await WritingAgent(llm_provider=provider).execute_task({"task": "T", "output_type": "report", "research_result": {"sources": [], "source_count": 0}})
        assert len(provider.calls) == 1

    @pytest.mark.asyncio
    async def test_fallback_preserves_template_content(self):
        agent = WritingAgent(llm_provider=FailingProvider())
        response = await agent.execute_task({"task": "T", "output_type": "report", "research_result": {"sources": [], "source_count": 0}})
        assert response.data["content"] != ""

    @pytest.mark.asyncio
    async def test_citations_built_from_sources_when_missing(self):
        agent = WritingAgent(llm_provider=FakeProvider("# content"))
        response = await agent.execute_task({
            "task": "T",
            "output_type": "report",
            "research_result": {"sources": [{"title": "S", "url": "https://s.com"}], "source_count": 1},
        })
        assert len(response.data["citations"]) == 1

    @pytest.mark.asyncio
    async def test_word_count_matches_llm_content(self):
        content = "one two three four"
        agent = WritingAgent(llm_provider=FakeProvider(content))
        response = await agent.execute_task({"task": "T", "output_type": "report", "research_result": {"sources": [], "source_count": 0}})
        assert response.data["word_count"] == 4

    @pytest.mark.asyncio
    async def test_source_count_preserved_with_llm(self):
        agent = WritingAgent(llm_provider=FakeProvider("# content"))
        response = await agent.execute_task({
            "task": "T",
            "output_type": "report",
            "research_result": {"sources": [{"title": "S", "url": "https://s.com"}], "source_count": 1},
        })
        assert response.data["source_count"] == 1

    @pytest.mark.asyncio
    async def test_llm_used_false_when_no_provider(self):
        response = await WritingAgent().execute_task({"task": "T", "output_type": "report", "research_result": {"sources": [], "source_count": 0}})
        assert response.metadata["llm_used"] is False

    @pytest.mark.asyncio
    async def test_llm_used_true_when_provider(self):
        response = await WritingAgent(llm_provider=FakeProvider("# content")).execute_task({"task": "T", "output_type": "report", "research_result": {"sources": [], "source_count": 0}})
        assert response.metadata["llm_used"] is True

