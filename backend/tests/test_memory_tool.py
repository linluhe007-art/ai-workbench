"""
MemoryTool 测试
覆盖：name/description、execute 成功、空结果、参数错误、registry 获取。
"""

import pytest
from unittest.mock import MagicMock

from app.tools.memory_tool import MemoryTool
from app.tools.base import ToolResult
from app.tools.registry import tool_registry


# === Mock MemoryService ===

def _mock_memory(results: list[dict] | None = None):
    mem = MagicMock()
    mem.search = MagicMock(return_value=results or [])
    return mem


SAMPLE_RESULTS = [
    {"title": "AI漫剧创作指南", "path": "03-技术笔记/AI漫剧.md", "summary": "关于AI漫剧的完整指南", "tags": ["AI", "创作"], "relevance": 0.8},
    {"title": "Docker优化笔记", "path": "03-技术笔记/Docker.md", "summary": "Docker安装和配置", "tags": ["Docker"], "relevance": 0.5},
]


# === name / description ===

class TestMemoryToolProperties:

    def test_name(self):
        tool = MemoryTool()
        assert tool.name == "memory_search"

    def test_description(self):
        tool = MemoryTool()
        assert "知识库" in tool.description or "memory" in tool.description.lower()


# === execute 成功 ===

class TestMemoryToolExecute:

    @pytest.mark.asyncio
    async def test_execute_returns_results(self):
        mem = _mock_memory(SAMPLE_RESULTS)
        tool = MemoryTool(memory_service=mem)

        result = await tool.execute(query="AI漫剧", limit=5)

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert "memories" in result.data
        assert len(result.data["memories"]) == 2

    @pytest.mark.asyncio
    async def test_execute_result_structure(self):
        mem = _mock_memory(SAMPLE_RESULTS)
        tool = MemoryTool(memory_service=mem)

        result = await tool.execute(query="AI")
        item = result.data["memories"][0]

        assert item["title"] == "AI漫剧创作指南"
        assert item["path"] == "03-技术笔记/AI漫剧.md"
        assert "AI" in item["tags"]
        assert item["relevance"] == 0.8

    @pytest.mark.asyncio
    async def test_execute_metadata(self):
        mem = _mock_memory(SAMPLE_RESULTS)
        tool = MemoryTool(memory_service=mem)

        result = await tool.execute(query="test", limit=3)

        assert result.metadata["query"] == "test"
        assert result.metadata["limit"] == 3
        assert result.metadata["count"] == 2

    @pytest.mark.asyncio
    async def test_execute_passes_limit(self):
        mem = _mock_memory([])
        tool = MemoryTool(memory_service=mem)

        await tool.execute(query="test", limit=10)
        mem.search.assert_called_once_with("test", limit=10)

    @pytest.mark.asyncio
    async def test_execute_default_limit(self):
        mem = _mock_memory([])
        tool = MemoryTool(memory_service=mem)

        await tool.execute(query="test")
        mem.search.assert_called_once_with("test", limit=5)


# === 空结果 ===

class TestMemoryToolEmpty:

    @pytest.mark.asyncio
    async def test_empty_result(self):
        mem = _mock_memory([])
        tool = MemoryTool(memory_service=mem)

        result = await tool.execute(query="不存在的内容")

        assert result.success is True
        assert result.data["memories"] == []
        assert result.metadata["count"] == 0


# === 参数错误 ===

class TestMemoryToolErrors:

    @pytest.mark.asyncio
    async def test_empty_query(self):
        tool = MemoryTool(memory_service=_mock_memory())
        result = await tool.execute(query="")
        assert result.success is False
        assert "query" in result.error

    @pytest.mark.asyncio
    async def test_none_query(self):
        tool = MemoryTool(memory_service=_mock_memory())
        result = await tool.execute(query=None)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_whitespace_query(self):
        tool = MemoryTool(memory_service=_mock_memory())
        result = await tool.execute(query="   ")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_invalid_limit_falls_back(self):
        mem = _mock_memory([])
        tool = MemoryTool(memory_service=mem)

        await tool.execute(query="test", limit=-1)
        mem.search.assert_called_once_with("test", limit=5)

    @pytest.mark.asyncio
    async def test_memory_exception_handled(self):
        mem = MagicMock()
        mem.search = MagicMock(side_effect=RuntimeError("DB connection lost"))
        tool = MemoryTool(memory_service=mem)

        result = await tool.execute(query="test")
        assert result.success is False
        assert "DB connection lost" in result.error


# === LLM Tool 格式 ===

class TestMemoryToolLLMFormat:

    def test_to_llm_tool(self):
        tool = MemoryTool()
        llm = tool.to_llm_tool()

        assert llm["type"] == "function"
        assert llm["function"]["name"] == "memory_search"
        assert "query" in llm["function"]["parameters"]["properties"]
        assert "query" in llm["function"]["parameters"]["required"]

    def test_parameters_schema(self):
        tool = MemoryTool()
        schema = tool._parameters_schema()

        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "limit" in schema["properties"]
        assert schema["required"] == ["query"]


# === Registry 集成 ===

class TestMemoryToolRegistry:

    def test_registered_on_import(self):
        assert "memory_search" in tool_registry

    def test_get_from_registry(self):
        tool = tool_registry.get("memory_search")
        assert tool is not None
        assert isinstance(tool, MemoryTool)
        assert tool.name == "memory_search"

    def test_in_list_tools(self):
        tools = tool_registry.list_tools()
        names = {t["name"] for t in tools}
        assert "memory_search" in names

    def test_in_list_llm_tools(self):
        llm_tools = tool_registry.list_llm_tools()
        names = {t["function"]["name"] for t in llm_tools}
        assert "memory_search" in names