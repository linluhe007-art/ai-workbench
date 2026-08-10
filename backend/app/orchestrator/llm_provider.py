"""
LLM Provider 统一接口
定义与大语言模型交互的标准接口。
支持：多轮对话、function calling、tool calling。
所有 LLM 适配器 (OpenAI/Claude/Gemini/DeepSeek/Ollama) 必须实现此接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LLMRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class LLMMessage:
    """对话消息"""
    role: LLMRole
    content: str
    name: str = ""
    tool_call_id: str = ""


@dataclass
class LLMTool:
    """工具定义 (用于 function calling)"""
    name: str
    description: str
    parameters: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = "stop"         # stop / length / tool_calls
    tool_calls: list[dict] = field(default_factory=list)  # function calling 结果
    metadata: dict = field(default_factory=dict)


class LLMProvider(ABC):
    """
    LLM Provider 抽象接口
    设计原则：
    - 支持多轮对话 (messages 列表)
    - 支持 function/tool calling (tools 参数)
    - 支持模型选择 (model 参数)
    - 支持参数调节 (temperature, max_tokens)
    """

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[LLMTool] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        多轮对话接口
        Args:
            messages: 对话消息列表
            model: 模型标识 (None 使用默认模型)
            temperature: 温度参数 (0-2)
            max_tokens: 最大生成 token 数
            tools: 可用工具列表 (function calling)
            **kwargs: 其他模型特有参数
        Returns:
            LLMResponse
        """
        ...

    async def complete(self, prompt: str, system: str = "", **kwargs: Any) -> LLMResponse:
        """
        单次补全便捷方法
        自动构建 messages 列表。
        """
        messages = []
        if system:
            messages.append(LLMMessage(role=LLMRole.SYSTEM, content=system))
        messages.append(LLMMessage(role=LLMRole.USER, content=prompt))
        return await self.chat(messages, **kwargs)

    @abstractmethod
    def get_model_name(self) -> str:
        """返回默认模型标识"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查 Provider 是否可用"""
        ...


class MockLLMProvider(LLMProvider):
    """
    Mock LLM Provider
    返回预设占位响应，用于开发和测试。
    """

    def __init__(self, default_model: str = "mock-llm-v1"):
        self.default_model = default_model

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[LLMTool] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        last_msg = messages[-1].content if messages else ""
        tool_info = f", tools={len(tools)}" if tools else ""
        return LLMResponse(
            content=f"[Mock LLM] 收到 {len(messages)} 条消息 (temp={temperature}{tool_info})。最后一条: {last_msg[:100]}",
            model=model or self.default_model,
            tokens_used=0,
            finish_reason="stop",
            metadata={"provider": "mock"},
        )

    def get_model_name(self) -> str:
        return self.default_model

    def is_available(self) -> bool:
        return True
class DeepSeekProvider(LLMProvider):
    """
    DeepSeek LLM Provider
    通过 OpenAI 兼容 API 调用 DeepSeek 模型。
    API 文档: https://platform.deepseek.com/api-docs
    """

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", default_model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def chat(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: list[LLMTool] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        import httpx

        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = [t.to_dict() for t in tools]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice["message"].get("content", ""),
            model=data.get("model", model or self.default_model),
            tokens_used=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            tool_calls=choice["message"].get("tool_calls", []),
            metadata={"provider": "deepseek"},
        )

    def get_model_name(self) -> str:
        return self.default_model

    def is_available(self) -> bool:
        return bool(self.api_key)