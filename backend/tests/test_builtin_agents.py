"""
内置 Agent 测试
覆盖：Registry 自动加载、各 Agent 执行、输出 schema 校验。
"""

import pytest

from app.agents.registry import AgentRegistry
from app.agents.research_agent import ResearchAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.writing_agent import WritingAgent
from app.agents.base import AgentResult


# === Registry 自动注册测试 ===

class TestBuiltinRegistration:

    def test_registry_has_three_agents(self):
        from app.agents.registry import registry
        agents = registry.list_agents()
        ids = {a["id"] for a in agents}
        assert "research" in ids
        assert "analysis" in ids
        assert "writing" in ids

    def test_registry_get_by_name(self):
        from app.agents.registry import registry
        assert registry.get("research") is not None
        assert registry.get("analysis") is not None
        assert registry.get("writing") is not None

    def test_fresh_registry_auto_register(self):
        reg = AgentRegistry()
        # _register_builtin_agents 在模块加载时已绑定到全局 registry
        # 新建的 registry 不会自动注册，这是预期行为
        assert len(reg) == 0


# === ResearchAgent ===

class TestResearchAgent:

    @pytest.mark.asyncio
    async def test_execute_returns_result(self):
        agent = ResearchAgent()
        result = await agent.execute("搜索AI最新新闻")

        assert isinstance(result, AgentResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_output_schema(self):
        agent = ResearchAgent()
        result = await agent.execute("AI新闻")
        data = result.output

        assert data["agent"] == "research"
        assert isinstance(data["topics"], list)
        assert len(data["topics"]) > 0
        assert isinstance(data["summary"], str)

    @pytest.mark.asyncio
    async def test_topic_structure(self):
        agent = ResearchAgent()
        result = await agent.execute("test")
        topic = result.output["topics"][0]

        assert "title" in topic
        assert "url" in topic
        assert "relevance" in topic

    def test_capabilities(self):
        agent = ResearchAgent()
        caps = agent.get_capabilities()
        assert "web_search" in caps
        assert "rss_parse" in caps


# === AnalysisAgent ===

class TestAnalysisAgent:

    @pytest.mark.asyncio
    async def test_execute_returns_result(self):
        agent = AnalysisAgent()
        result = await agent.execute("分析AI趋势")

        assert isinstance(result, AgentResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_output_schema(self):
        agent = AnalysisAgent()
        result = await agent.execute("分析趋势")
        data = result.output

        assert data["agent"] == "analysis"
        assert isinstance(data["score"], (int, float))
        assert 0 <= data["score"] <= 10
        assert isinstance(data["recommendation"], str)

    @pytest.mark.asyncio
    async def test_with_upstream_context(self):
        agent = AnalysisAgent()
        context = {
            "research": {
                "topics": [{"title": "t1"}, {"title": "t2"}],
                "summary": "test",
            }
        }
        result = await agent.execute("分析", context=context)
        data = result.output

        assert data["details"]["topics_analyzed"] == 2

    def test_capabilities(self):
        agent = AnalysisAgent()
        caps = agent.get_capabilities()
        assert "content_eval" in caps
        assert "trend_analysis" in caps


# === WritingAgent ===

class TestWritingAgent:

    @pytest.mark.asyncio
    async def test_execute_returns_result(self):
        agent = WritingAgent()
        result = await agent.execute("写一篇AI文章")

        assert isinstance(result, AgentResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_output_schema(self):
        agent = WritingAgent()
        result = await agent.execute("AI技术突破")
        data = result.output

        assert data["agent"] == "writing"
        assert isinstance(data["title"], str)
        assert len(data["title"]) > 0
        assert isinstance(data["content"], str)
        assert len(data["content"]) > 0
        assert isinstance(data["tags"], list)
        assert isinstance(data["word_count"], int)

    @pytest.mark.asyncio
    async def test_content_has_markdown(self):
        agent = WritingAgent()
        result = await agent.execute("AI")
        content = result.output["content"]

        assert content.startswith("#")
        assert "##" in content

    def test_capabilities(self):
        agent = WritingAgent()
        caps = agent.get_capabilities()
        assert "article_gen" in caps
        assert "script_gen" in caps


# === Agent 属性测试 ===

class TestAgentProperties:

    def test_research_agent_properties(self):
        agent = ResearchAgent()
        assert agent.id == "research"
        assert agent.name == "research"
        assert "research" in agent.description.lower() or "采集" in agent.description

    def test_analysis_agent_properties(self):
        agent = AnalysisAgent()
        assert agent.id == "analysis"
        assert agent.name == "analysis"

    def test_writing_agent_properties(self):
        agent = WritingAgent()
        assert agent.id == "writing"
        assert agent.name == "writing"

    def test_all_agents_online(self):
        from app.agents.registry import registry
        for agent_dict in registry.list_agents():
            assert agent_dict["status"] == "online"