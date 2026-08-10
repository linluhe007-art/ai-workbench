"""
Tool Calling Runtime 测试
覆盖：ToolCall 解析、ToolExecutor、Registry 调用、Agent tool loop、fallback。
"""

import json
import pytest

from app.tools.base import ToolCall, ToolResult, BaseTool
from app.tools.executor import ToolExecutor, ToolCallResult, ToolExecutionReport
from app.tools.registry import ToolRegistry
from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentType, AgentResult
from app.orchestrator.llm_provider import LLMProvider, LLMResponse, LLMMessage


# === 测试用工具 ===

class EchoTool(BaseTool):
    @property
    def name(self): return "echo"
    @property
    def description(self): return "回显输入"
    async def execute(self, **kwargs): return ToolResult(success=True, data=kwargs.get("text", ""))
    def _parameters_schema(self):
        return {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}


class AddTool(BaseTool):
    @property
    def name(self): return "add"
    @property
    def description(self): return "加法"
    async def execute(self, **kwargs): return ToolResult(success=True, data=kwargs.get("a", 0) + kwargs.get("b", 0))
    def _parameters_schema(self):
        return {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}


class FailTool(BaseTool):
    @property
    def name(self): return "fail"
    @property
    def description(self): return "失败工具"
    async def execute(self, **kwargs): raise RuntimeError("tool broke")


# === 测试用可控 LLM ===

class ScriptedLLM(LLMProvider):
    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self._call_count = 0
        self._calls: list[dict] = []

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        self._call_count += 1
        self._calls.append({"messages": messages, "tools": tools})
        if self._responses:
            return self._responses.pop(0)
        return LLMResponse(content="done", model="scripted", finish_reason="stop")

    def get_model_name(self): return "scripted"
    def is_available(self): return True


# === ToolCall 解析 ===

class TestToolCallParsing:

    def test_from_llm_dict_openai_format(self):
        data = {
            "id": "call_001",
            "function": {
                "name": "echo",
                "arguments": json.dumps({"text": "hello"}),
            }
        }
        tc = ToolCall.from_llm_dict(data)
        assert tc.id == "call_001"
        assert tc.name == "echo"
        assert tc.arguments == {"text": "hello"}

    def test_from_llm_dict_empty_args(self):
        data = {"id": "c2", "function": {"name": "test", "arguments": "{}"}}
        tc = ToolCall.from_llm_dict(data)
        assert tc.arguments == {}

    def test_from_llm_dict_invalid_json(self):
        data = {"id": "c3", "function": {"name": "test", "arguments": "not-json"}}
        tc = ToolCall.from_llm_dict(data)
        assert tc.arguments == {}

    def test_from_llm_dict_dict_args(self):
        data = {"id": "c4", "function": {"name": "test", "arguments": {"a": 1}}}
        tc = ToolCall.from_llm_dict(data)
        assert tc.arguments == {"a": 1}

    def test_from_llm_dict_missing_fields(self):
        data = {}
        tc = ToolCall.from_llm_dict(data)
        assert tc.id == ""
        assert tc.name == ""


# === ToolExecutor ===

class TestToolExecutor:

    @pytest.mark.asyncio
    async def test_execute_single_tool(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        executor = ToolExecutor(reg)

        tc = ToolCall(id="c1", name="echo", arguments={"text": "hi"})
        result = await executor.execute(tc)

        assert result.tool_call.id == "c1"
        assert result.result.success is True
        assert result.result.data == "hi"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        reg = ToolRegistry()
        executor = ToolExecutor(reg)

        tc = ToolCall(id="c1", name="nonexistent", arguments={})
        result = await executor.execute(tc)

        assert result.result.success is False
        assert "not found" in result.result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_exception(self):
        reg = ToolRegistry()
        reg.register(FailTool())
        executor = ToolExecutor(reg)

        tc = ToolCall(id="c1", name="fail", arguments={})
        result = await executor.execute(tc)

        assert result.result.success is False
        assert "tool broke" in result.result.error

    @pytest.mark.asyncio
    async def test_execute_all(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        reg.register(AddTool())
        executor = ToolExecutor(reg)

        calls = [
            ToolCall(id="c1", name="echo", arguments={"text": "hello"}),
            ToolCall(id="c2", name="add", arguments={"a": 3, "b": 4}),
        ]
        report = await executor.execute_all(calls)

        assert report.all_success is True
        assert report.success_count == 2
        assert report.failure_count == 0

    @pytest.mark.asyncio
    async def test_execute_all_partial_failure(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        reg.register(FailTool())
        executor = ToolExecutor(reg)

        calls = [
            ToolCall(id="c1", name="echo", arguments={"text": "ok"}),
            ToolCall(id="c2", name="fail", arguments={}),
        ]
        report = await executor.execute_all(calls)

        assert report.all_success is False
        assert report.success_count == 1
        assert report.failure_count == 1


# === ToolExecutionReport ===

class TestToolExecutionReport:

    @pytest.mark.asyncio
    async def test_to_llm_messages(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        executor = ToolExecutor(reg)

        tc = ToolCall(id="c1", name="echo", arguments={"text": "hello"})
        report = await executor.execute_all([tc])

        messages = report.to_llm_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "c1"
        assert "hello" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_to_llm_messages_error(self):
        reg = ToolRegistry()
        reg.register(FailTool())
        executor = ToolExecutor(reg)

        tc = ToolCall(id="c1", name="fail", arguments={})
        report = await executor.execute_all([tc])

        messages = report.to_llm_messages()
        assert messages[0]["role"] == "tool"
        assert "Error" in messages[0]["content"]


# === Agent run_with_tools ===

class TestAgentRunWithTools:

    @pytest.mark.asyncio
    async def test_no_llm_fallback_to_execute_task(self):
        """无 LLM Provider 时 fallback 到 execute_task"""
        agent = EchoAgent()
        result = await agent.run_with_tools("测试")

        assert result.success is True
        assert "task" in result.output

    @pytest.mark.asyncio
    async def test_llm_no_tool_calls(self):
        """LLM 直接返回文本（无 tool_calls）"""
        llm = ScriptedLLM([
            LLMResponse(content="最终回答", model="test", finish_reason="stop"),
        ])
        agent = EchoAgent()
        agent.set_llm_provider(llm)

        result = await agent.run_with_tools("你好")
        assert result.success is True
        assert result.output["response"] == "最终回答"

    @pytest.mark.asyncio
    async def test_llm_with_tool_call_loop(self):
        """LLM 先调用工具，再返回最终文本"""
        llm = ScriptedLLM([
            LLMResponse(content="", model="test", finish_reason="tool_calls",
                        tool_calls=[{"id": "c1", "function": {"name": "echo", "arguments": '{"text":"hello"}'}}]),
            LLMResponse(content="工具结果已处理", model="test", finish_reason="stop"),
        ])

        reg = ToolRegistry()
        reg.register(EchoTool())

        agent = EchoAgent()
        agent.set_llm_provider(llm)
        agent.set_tool_registry(reg)

        result = await agent.run_with_tools("调用工具")
        assert result.success is True
        assert result.output["response"] == "工具结果已处理"
        assert llm._call_count == 2

    @pytest.mark.asyncio
    async def test_tool_results_sent_back_to_llm(self):
        """工具结果正确回传给 LLM"""
        llm = ScriptedLLM([
            LLMResponse(content="", model="test", finish_reason="tool_calls",
                        tool_calls=[{"id": "c1", "function": {"name": "add", "arguments": '{"a":1,"b":2}'}}]),
            LLMResponse(content="3", model="test", finish_reason="stop"),
        ])

        reg = ToolRegistry()
        reg.register(AddTool())

        agent = EchoAgent()
        agent.set_llm_provider(llm)
        agent.set_tool_registry(reg)

        result = await agent.run_with_tools("计算1+2")
        assert result.success is True
        # 验证第二次调用时 messages 包含 tool 结果
        second_call = llm._calls[1]
        tool_msgs = [m for m in second_call["messages"] if hasattr(m, 'role') and m.role.value == "tool"]
        assert len(tool_msgs) > 0

    @pytest.mark.asyncio
    async def test_no_tools_still_works(self):
        """Agent 没有注册 Tool 时正常工作"""
        llm = ScriptedLLM([
            LLMResponse(content="无工具回答", model="test", finish_reason="stop"),
        ])

        agent = EchoAgent()
        agent.set_llm_provider(llm)
        # 不设置 tool_registry

        result = await agent.run_with_tools("你好")
        assert result.success is True
        assert result.output["response"] == "无工具回答"


# === 辅助 Agent ===

class EchoAgent(BaseAgent):
    def __init__(self):
        config = AgentConfig(id="echo-agent", name="Echo", type=AgentType.CUSTOM)
        super().__init__(config)

    async def chat(self, message, context=None):
        return f"[Echo] {message}"

    async def execute_task(self, task_input):
        return AgentResponse(success=True, data={"task": task_input.get("task", ""), "type": "mock"})

    def get_capabilities(self):
        return ["echo"]