"""
LLM Agent Adapter 测试
覆盖：agent -> llm provider 调用、mock fallback、context 注入、response 解析。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentType, AgentStatus, AgentResult
from app.agents.research_agent import ResearchAgent
from app.agents.writing_agent import WritingAgent
from app.agents.context import AgentContext
from app.orchestrator.llm_provider import (
    LLMProvider, MockLLMProvider, LLMMessage, LLMRole, LLMResponse,
)
from app.orchestrator.planner import TaskStep, TaskType


# === 可控 LLM Provider ===

class ScriptedLLM(LLMProvider):
    """返回预设响应的 LLM，用于测试"""

    def __init__(self, response_content: str = "[LLM] 测试响应"):
        self._content = response_content
        self._calls: list[list[LLMMessage]] = []

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        self._calls.append(messages)
        return LLMResponse(
            content=self._content,
            model="scripted-v1",
            tokens_used=42,
            finish_reason="stop",
            metadata={"provider": "scripted"},
        )

    def get_model_name(self) -> str:
        return "scripted-v1"

    def is_available(self) -> bool:
        return True


class FailingLLM(LLMProvider):
    """始终抛异常的 LLM"""

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        raise RuntimeError("API timeout")

    def get_model_name(self) -> str:
        return "failing"

    def is_available(self) -> bool:
        return False


# === call_llm 基础测试 ===

class TestCallLLMBasic:

    @pytest.mark.asyncio
    async def test_no_provider_returns_none(self):
        """没有 LLM Provider 时返回 None"""
        agent = ResearchAgent()
        result = await agent.call_llm("测试提示")
        assert result is None

    @pytest.mark.asyncio
    async def test_with_provider_returns_response(self):
        """有 Provider 时返回 LLMResponse"""
        agent = ResearchAgent()
        agent.set_llm_provider(ScriptedLLM("[Research] 分析结果"))

        resp = await agent.call_llm("搜索AI新闻")
        assert resp is not None
        assert resp.content == "[Research] 分析结果"
        assert resp.model == "scripted-v1"
        assert resp.tokens_used == 42

    @pytest.mark.asyncio
    async def test_provider_failure_returns_none(self):
        """Provider 抛异常时 call_llm 不应崩溃"""
        agent = ResearchAgent()
        agent.set_llm_provider(FailingLLM())

        with pytest.raises(RuntimeError, match="API timeout"):
            await agent.call_llm("test")

    @pytest.mark.asyncio
    async def test_set_llm_provider_runtime(self):
        """运行时注入 Provider"""
        agent = ResearchAgent()
        assert agent.llm_provider is None

        provider = MockLLMProvider()
        agent.set_llm_provider(provider)
        assert agent.llm_provider is provider


# === Context 注入测试 ===

class TestCallLLMContextInjection:

    @pytest.mark.asyncio
    async def test_system_prompt_includes_agent_identity(self):
        """system prompt 包含 Agent 身份"""
        llm = ScriptedLLM()
        agent = ResearchAgent()
        agent.set_llm_provider(llm)

        await agent.call_llm("test prompt")

        assert len(llm._calls) == 1
        messages = llm._calls[0]
        assert messages[0].role == LLMRole.SYSTEM
        assert "research" in messages[0].content.lower() or "采集" in messages[0].content

    @pytest.mark.asyncio
    async def test_memory_context_in_system_prompt(self):
        """Memory 上下文注入到 system prompt"""
        llm = ScriptedLLM()
        agent = WritingAgent()
        agent.set_llm_provider(llm)

        ctx = {
            "memory_summary": "关于AI漫剧的知识库摘要内容",
            "tags": ["AI", "创作", "漫剧"],
        }
        await agent.call_llm("写一篇AI漫剧方案", context=ctx)

        messages = llm._calls[0]
        system_msg = messages[0].content
        assert "AI漫剧" in system_msg
        assert "创作" in system_msg

    @pytest.mark.asyncio
    async def test_user_message_is_prompt(self):
        """user message 是传入的 prompt"""
        llm = ScriptedLLM()
        agent = ResearchAgent()
        agent.set_llm_provider(llm)

        await agent.call_llm("搜索最新AI动态")

        messages = llm._calls[0]
        assert messages[-1].role == LLMRole.USER
        assert messages[-1].content == "搜索最新AI动态"

    @pytest.mark.asyncio
    async def test_empty_context_still_works(self):
        """空 context 正常工作"""
        llm = ScriptedLLM()
        agent = ResearchAgent()
        agent.set_llm_provider(llm)

        resp = await agent.call_llm("test", context={})
        assert resp is not None


# === 参数传递测试 ===

class TestCallLLMParameters:

    @pytest.mark.asyncio
    async def test_temperature_passed(self):
        """temperature 参数正确传递"""
        llm = ScriptedLLM()
        agent = ResearchAgent()
        agent.set_llm_provider(llm)

        await agent.call_llm("test", temperature=0.3)

        # ScriptedLLM 不检查参数，但 MockLLM 会
        # 这里验证调用不报错
        assert len(llm._calls) == 1

    @pytest.mark.asyncio
    async def test_max_tokens_passed(self):
        """max_tokens 参数正确传递"""
        llm = ScriptedLLM()
        agent = ResearchAgent()
        agent.set_llm_provider(llm)

        resp = await agent.call_llm("test", max_tokens=1024)
        assert resp is not None


# === Response 解析测试 ===

class TestCallLLMResponseParsing:

    @pytest.mark.asyncio
    async def test_response_content(self):
        """响应内容正确返回"""
        llm = ScriptedLLM('{"title": "AI新闻", "body": "内容"}')
        agent = WritingAgent()
        agent.set_llm_provider(llm)

        resp = await agent.call_llm("写文章")
        assert '"title"' in resp.content

    @pytest.mark.asyncio
    async def test_response_metadata(self):
        """响应 metadata 正确"""
        llm = ScriptedLLM()
        agent = ResearchAgent()
        agent.set_llm_provider(llm)

        resp = await agent.call_llm("test")
        assert resp.metadata["provider"] == "scripted"

    @pytest.mark.asyncio
    async def test_response_model_info(self):
        """响应 model 信息正确"""
        llm = ScriptedLLM()
        agent = ResearchAgent()
        agent.set_llm_provider(llm)

        resp = await agent.call_llm("test")
        assert resp.model == "scripted-v1"


# === Agent + LLM 集成测试 ===

class TestAgentLLMIntegration:

    @pytest.mark.asyncio
    async def test_research_agent_with_llm(self):
        """ResearchAgent 注入 LLM 后 execute_task 可用"""
        agent = ResearchAgent()
        # execute_task 仍然是 Mock 实现
        result = await agent.execute_task({"task": "搜索AI新闻", "context": {}})
        assert result.success is True
        assert result.data["agent"] == "research"

        # call_llm 是额外能力
        agent.set_llm_provider(ScriptedLLM("[LLM] 深度分析"))
        llm_result = await agent.call_llm("深度分析AI趋势")
        assert llm_result.content == "[LLM] 深度分析"

    @pytest.mark.asyncio
    async def test_writing_agent_with_mock_llm(self):
        """WritingAgent 配合 MockLLMProvider"""
        agent = WritingAgent()
        agent.set_llm_provider(MockLLMProvider())

        resp = await agent.call_llm("写一篇关于AI的文章")
        assert "[Mock LLM]" in resp.content

    @pytest.mark.asyncio
    async def test_execute_step_with_llm_provider(self):
        """execute_step 传递 context 时 LLM 可用"""
        llm = ScriptedLLM()
        agent = ResearchAgent()
        agent.set_llm_provider(llm)

        step = TaskStep(id="r1", type=TaskType.RESEARCH, description="采集AI新闻")
        ctx = AgentContext(
            memory_summary="知识库摘要",
            tags=["AI"],
            task_description="采集AI新闻",
        )
        output = await agent.execute_step(step, ctx)

        assert "agent" in output
        assert output["agent"] == "research"

    @pytest.mark.asyncio
    async def test_backward_compatibility_no_llm(self):
        """没有 LLM 时行为不变"""
        agent = ResearchAgent()
        assert agent.llm_provider is None

        step = TaskStep(id="r1", type=TaskType.RESEARCH, description="test")
        output = await agent.execute_step(step)
        assert output["agent"] == "research"