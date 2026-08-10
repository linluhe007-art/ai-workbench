from app.tools.base import BaseTool, ToolResult, ToolCall
from app.tools.registry import ToolRegistry, tool_registry
from app.tools.executor import ToolExecutor, ToolCallResult, ToolExecutionReport
from app.tools.memory_tool import MemoryTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolCall",
    "ToolRegistry",
    "tool_registry",
    "ToolExecutor",
    "ToolCallResult",
    "ToolExecutionReport",
    "MemoryTool",
]


def _register_builtin_tools(reg: ToolRegistry):
    """注册内置 Tool"""
    reg.register(MemoryTool())


_register_builtin_tools(tool_registry)