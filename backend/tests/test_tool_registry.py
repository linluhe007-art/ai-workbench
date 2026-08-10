"""
Tool 基础框架测试
覆盖：BaseTool 接口、ToolResult、ToolRegistry CRUD、to_llm_tool。
"""

import pytest

from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry, tool_registry


# === 测试用 Tool 实现 ===

class EchoTool(BaseTool):
    """返回输入的简单工具"""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "返回输入的文本"

    async def execute(self, **kwargs) -> ToolResult:
        text = kwargs.get("text", "")
        return ToolResult(success=True, data=text)

    def _parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要回显的文本"},
            },
            "required": ["text"],
        }


class FailTool(BaseTool):
    """始终失败的工具"""

    @property
    def name(self) -> str:
        return "fail"

    @property
    def description(self) -> str:
        return "总是失败的工具"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=False, error="intentional failure")


class CalculatorTool(BaseTool):
    """简单加法工具"""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "执行简单数学计算"

    async def execute(self, **kwargs) -> ToolResult:
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        op = kwargs.get("op", "add")
        if op == "add":
            return ToolResult(success=True, data=a + b)
        return ToolResult(success=False, error=f"Unknown op: {op}")

    def _parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "第一个数"},
                "b": {"type": "number", "description": "第二个数"},
                "op": {"type": "string", "description": "操作类型"},
            },
            "required": ["a", "b"],
        }


# === ToolResult 测试 ===

class TestToolResult:

    def test_success_result(self):
        r = ToolResult(success=True, data="hello")
        assert r.success is True
        assert r.data == "hello"
        assert r.error == ""

    def test_failure_result(self):
        r = ToolResult(success=False, error="boom")
        assert r.success is False
        assert r.error == "boom"

    def test_default_metadata(self):
        r = ToolResult(success=True)
        assert r.metadata == {}


# === BaseTool 接口测试 ===

class TestBaseTool:

    @pytest.mark.asyncio
    async def test_echo_execute(self):
        tool = EchoTool()
        result = await tool.execute(text="hello")
        assert result.success is True
        assert result.data == "hello"

    @pytest.mark.asyncio
    async def test_fail_execute(self):
        tool = FailTool()
        result = await tool.execute()
        assert result.success is False
        assert "intentional" in result.error

    @pytest.mark.asyncio
    async def test_calculator(self):
        tool = CalculatorTool()
        result = await tool.execute(a=3, b=4, op="add")
        assert result.success is True
        assert result.data == 7

    def test_to_dict(self):
        tool = EchoTool()
        d = tool.to_dict()
        assert d["name"] == "echo"
        assert d["description"] == "返回输入的文本"


# === to_llm_tool 测试 ===

class TestToLLMTool:

    def test_basic_llm_tool_format(self):
        tool = EchoTool()
        llm = tool.to_llm_tool()

        assert llm["type"] == "function"
        assert llm["function"]["name"] == "echo"
        assert llm["function"]["description"] == "返回输入的文本"
        assert "parameters" in llm["function"]

    def test_parameters_schema(self):
        tool = CalculatorTool()
        llm = tool.to_llm_tool()
        params = llm["function"]["parameters"]

        assert params["type"] == "object"
        assert "a" in params["properties"]
        assert "b" in params["properties"]
        assert "required" in params

    def test_default_empty_parameters(self):
        """未覆盖 _parameters_schema 时返回空 object"""

        class MinimalTool(BaseTool):
            @property
            def name(self): return "minimal"
            @property
            def description(self): return "minimal tool"
            async def execute(self, **kwargs): return ToolResult(success=True)

        llm = MinimalTool().to_llm_tool()
        assert llm["function"]["parameters"]["type"] == "object"


# === ToolRegistry 测试 ===

class TestToolRegistry:

    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = EchoTool()
        reg.register(tool)

        assert reg.get("echo") is tool

    def test_get_nonexistent(self):
        reg = ToolRegistry()
        assert reg.get("nope") is None

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        reg.register(CalculatorTool())

        tools = reg.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"echo", "calculator"}

    def test_list_llm_tools(self):
        reg = ToolRegistry()
        reg.register(EchoTool())

        llm_tools = reg.list_llm_tools()
        assert len(llm_tools) == 1
        assert llm_tools[0]["type"] == "function"
        assert llm_tools[0]["function"]["name"] == "echo"

    def test_unregister(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        assert reg.unregister("echo") is True
        assert reg.get("echo") is None
        assert reg.unregister("echo") is False

    def test_clear(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        reg.register(CalculatorTool())
        reg.clear()
        assert len(reg) == 0

    def test_contains(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        assert "echo" in reg
        assert "nope" not in reg

    def test_len(self):
        reg = ToolRegistry()
        assert len(reg) == 0
        reg.register(EchoTool())
        assert len(reg) == 1

    def test_overwrite_warning(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        reg.register(EchoTool())  # 不报错，只 warning
        assert len(reg) == 1


# === 全局 tool_registry 测试 ===

class TestGlobalToolRegistry:

    def test_global_instance_exists(self):
        assert tool_registry is not None
        assert isinstance(tool_registry, ToolRegistry)

    def test_register_to_global(self):
        tool_registry.register(EchoTool())
        assert tool_registry.get("echo") is not None
        # 清理
        tool_registry.unregister("echo")