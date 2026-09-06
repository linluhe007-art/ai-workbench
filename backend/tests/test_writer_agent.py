"""Phase Beta-Search tests - WritingAgent"""
import pytest
from app.agents.writing_agent import WritingAgent, OUTPUT_TEMPLATES


class TestOutputTemplates:
    def test_report_template(self):
        assert "report" in OUTPUT_TEMPLATES
        assert "{title}" in OUTPUT_TEMPLATES["report"]
        assert "{source_count}" in OUTPUT_TEMPLATES["report"]

    def test_article_template(self):
        assert "article" in OUTPUT_TEMPLATES
        assert "{body}" in OUTPUT_TEMPLATES["article"]

    def test_analysis_template(self):
        assert "analysis" in OUTPUT_TEMPLATES
        assert "{problem}" in OUTPUT_TEMPLATES["analysis"]


class TestWritingAgentExecute:
    @pytest.mark.asyncio
    async def test_execute_task_report(self):
        agent = WritingAgent()
        resp = await agent.execute_task({
            "task": "AI trends",
            "output_type": "report",
            "research_result": {
                "sources": [{"title": "S1", "url": "https://s1.com"}],
                "source_count": 1,
                "citations": [],
            },
        })
        assert resp.success is True
        assert "content" in resp.data
        assert resp.data["output_type"] == "report"

    @pytest.mark.asyncio
    async def test_execute_task_article(self):
        agent = WritingAgent()
        resp = await agent.execute_task({
            "task": "Test topic",
            "output_type": "article",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert resp.data["output_type"] == "article"
        assert resp.data["content"] != ""

    @pytest.mark.asyncio
    async def test_execute_task_analysis(self):
        agent = WritingAgent()
        resp = await agent.execute_task({
            "task": "Market analysis",
            "output_type": "analysis",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert resp.data["output_type"] == "analysis"
        assert "problem" in resp.data["content"].lower() or "Analysis" in resp.data["content"]

    @pytest.mark.asyncio
    async def test_execute_task_includes_source_count(self):
        agent = WritingAgent()
        resp = await agent.execute_task({
            "task": "X",
            "output_type": "report",
            "research_result": {
                "sources": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
                "source_count": 3,
            },
        })
        assert resp.data["source_count"] == 3

    @pytest.mark.asyncio
    async def test_execute_task_content_has_title(self):
        agent = WritingAgent()
        resp = await agent.execute_task({
            "task": "AI Development",
            "output_type": "report",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert "AI Development" in resp.data["content"]

    @pytest.mark.asyncio
    async def test_execute_task_default_type_is_report(self):
        agent = WritingAgent()
        resp = await agent.execute_task({
            "task": "test",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert resp.data["output_type"] == "report"

    @pytest.mark.asyncio
    async def test_execute_task_with_citations(self):
        agent = WritingAgent()
        citations = [{"title": "Source A", "url": "https://a.com"}]
        resp = await agent.execute_task({
            "task": "test",
            "research_result": {
                "sources": [{"title": "S", "url": "https://s.com"}],
                "source_count": 1,
                "citations": citations,
            },
        })
        assert len(resp.data["citations"]) >= 1

    @pytest.mark.asyncio
    async def test_execute_task_records_duration(self):
        agent = WritingAgent()
        resp = await agent.execute_task({
            "task": "test",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert resp.duration_ms > 0

    @pytest.mark.asyncio
    async def test_chat_returns_string(self):
        agent = WritingAgent()
        result = await agent.chat("write about AI")
        assert "WritingAgent" in result

    def test_get_capabilities(self):
        agent = WritingAgent()
        caps = agent.get_capabilities()
        assert "markdown_generate" in caps
        assert "report_generate" in caps
        assert "content_write" in caps


class TestWritingAgentConfig:
    def test_agent_type(self):
        agent = WritingAgent()
        from app.agents.base import AgentType
        assert agent.config.type == AgentType.WRITING

    def test_agent_id(self):
        agent = WritingAgent()
        assert agent.id == "writing"
