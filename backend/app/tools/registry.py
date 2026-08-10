"""
Tool Registry
集中注册和管理所有 Tool 实例。
风格与 AgentRegistry 一致。
提供全局单例 tool_registry。
"""

from app.tools.base import BaseTool
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """
    Tool 注册中心
    管理所有已注册 Tool 的生命周期和查找。
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """注册 Tool (以 tool.name 为 key)"""
        if tool.name in self._tools:
            logger.warning("Tool already registered, overwriting", tool_name=tool.name)
        self._tools[tool.name] = tool
        logger.info("Tool registered", tool_name=tool.name)

    def get(self, name: str) -> BaseTool | None:
        """按 name 查找 Tool"""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """返回所有已注册 Tool 的摘要列表"""
        return [tool.to_dict() for tool in self._tools.values()]

    def list_llm_tools(self) -> list[dict]:
        """返回所有 Tool 的 LLM function calling 格式"""
        return [tool.to_llm_tool() for tool in self._tools.values()]

    def unregister(self, name: str) -> bool:
        """注销 Tool"""
        if name in self._tools:
            del self._tools[name]
            logger.info("Tool unregistered", tool_name=name)
            return True
        return False

    def clear(self):
        """清空所有注册"""
        self._tools.clear()

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# 全局单例
tool_registry = ToolRegistry()