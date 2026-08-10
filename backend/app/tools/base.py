"""
BaseTool 抽象基类 + ToolResult 数据结构
所有 Tool 必须继承此接口。
to_llm_tool() 可转换为 LLMTool 供 function calling 使用。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Tool 执行结果"""
    success: bool
    data: Any = None
    error: str = ""
    metadata: dict = field(default_factory=dict)



@dataclass
class ToolCall:
    """
    LLM 返回的工具调用请求
    对应 OpenAI function calling 的 tool_call 结构。
    """
    id: str                        # 调用 ID (用于回传结果)
    name: str                      # 工具名称
    arguments: dict = field(default_factory=dict)  # 工具参数

    @classmethod
    def from_llm_dict(cls, data: dict) -> "ToolCall":
        """
        从 LLM 响应的 tool_call dict 解析
        支持 OpenAI 格式:
        {"id": "...", "function": {"name": "...", "arguments": "{...}"}}
        """
        import json
        func = data.get("function", {})
        raw_args = func.get("arguments", "{}")
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except (json.JSONDecodeError, TypeError):
                args = {}
        else:
            args = raw_args if isinstance(raw_args, dict) else {}
        return cls(
            id=data.get("id", ""),
            name=func.get("name", ""),
            arguments=args,
        )

class BaseTool(ABC):
    """
    Tool 抽象基类
    所有工具必须实现 name、description、execute()。
    to_llm_tool() 提供 LLM function calling 元数据。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称 (唯一标识)"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述 (供 LLM 理解用途)"""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        执行工具
        Args:
            **kwargs: 工具参数
        Returns:
            ToolResult
        """
        ...

    def to_llm_tool(self) -> dict:
        """
        转换为 LLM function calling 格式
        默认基于 name/description 生成，子类可覆盖提供 parameters schema。
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._parameters_schema(),
            },
        }

    def _parameters_schema(self) -> dict:
        """
        返回参数 JSON Schema
        子类应覆盖此方法提供具体参数定义。
        """
        return {
            "type": "object",
            "properties": {},
        }

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
        }