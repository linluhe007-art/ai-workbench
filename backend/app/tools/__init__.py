from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry, tool_registry
from app.tools.memory_tool import MemoryTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "tool_registry",
    "MemoryTool",
]


def _register_builtin_tools(reg: ToolRegistry):
    """注册内置 Tool"""
    reg.register(MemoryTool())


_register_builtin_tools(tool_registry)