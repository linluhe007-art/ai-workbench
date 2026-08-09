"""
LLMProvider 测试
覆盖：Mock provider、接口兼容性、配置加载。
"""

import pytest

from app.orchestrator.llm_config import LLMConfig, create_llm_provider, load_llm_config
from app.orchestrator.llm_provider import (
    LLMMessage,
    LLMRole,
    LLMTool,
    MockLLMProvider,
)


class TestMockLLMProvider:

    @pytest.mark.asyncio
    async def test_chat_basic(self):
        provider = MockLLMProvider()
        messages = [LLMMessage(role=LLMRole.USER, content="你好")]
        resp = await provider.chat(messages)
        assert "[Mock LLM]" in resp.content
        assert resp.model == "mock-llm-v1"

    @pytest.mark.asyncio
    async def test_chat_with_tools(self):
        provider = MockLLMProvider()
        tools = [LLMTool(name="search", description="搜索工具")]
        messages = [LLMMessage(role=LLMRole.USER, content="搜索AI新闻")]
        resp = await provider.chat(messages, tools=tools, temperature=0.5)
        assert "tools=1" in resp.content

    @pytest.mark.asyncio
    async def test_complete(self):
        provider = MockLLMProvider()
        resp = await provider.complete("测试提示", system="你是一个助手")
        assert resp.content

    def test_is_available(self):
        provider = MockLLMProvider()
        assert provider.is_available() is True

    def test_model_name(self):
        provider = MockLLMProvider(default_model="test-model")
        assert provider.get_model_name() == "test-model"


class TestLLMConfig:

    def test_load_default_config(self):
        config = load_llm_config()
        assert config.provider in ("mock", "deepseek", "openai", "ollama")
        assert config.temperature >= 0

    def test_create_mock_provider(self):
        config = LLMConfig(provider="mock", model="test")
        provider = create_llm_provider(config)
        assert isinstance(provider, MockLLMProvider)

    def test_unknown_provider_fallback(self):
        config = LLMConfig(provider="nonexistent")
        provider = create_llm_provider(config)
        assert isinstance(provider, MockLLMProvider)


class TestLLMInterface:

    def test_llm_message(self):
        msg = LLMMessage(role=LLMRole.USER, content="hello")
        assert msg.role == LLMRole.USER

    def test_llm_tool_to_dict(self):
        tool = LLMTool(name="search", description="搜索", parameters={"type": "object"})
        d = tool.to_dict()
        assert d["type"] == "function"
        assert d["function"]["name"] == "search"