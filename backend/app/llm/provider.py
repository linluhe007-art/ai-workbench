"""LLM provider abstraction (Phase Beta-LLM)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.llm.models import LLMMessage, LLMResponse, normalize_messages


class LLMProvider(ABC):
    """Base interface implemented by every LLM provider."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage | dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion from a list of conversation messages."""
        raise NotImplementedError

    def get_model_name(self) -> str:
        return "unknown"

    def is_configured(self) -> bool:
        """Return True when the provider can actually make API calls."""
        return True


class MockLLMProvider(LLMProvider):
    """Deterministic provider for local development and tests."""

    def __init__(self, default_model: str = "mock-llm-v1") -> None:
        self.default_model = default_model

    async def generate(
        self,
        messages: list[LLMMessage | dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> LLMResponse:
        normalized = normalize_messages(messages)
        last = normalized[-1].content if normalized else ""
        selected_model = model or self.default_model
        return LLMResponse(
            content="[Mock LLM] Responding to " + str(len(normalized)) + " message(s). Last: " + last[:120],
            model=selected_model,
            input_tokens=sum(len(m.content) for m in normalized),
            output_tokens=len(last),
            finish_reason="stop",
            metadata={"provider": "mock"},
        )

    def get_model_name(self) -> str:
        return self.default_model

    def is_configured(self) -> bool:
        return True
