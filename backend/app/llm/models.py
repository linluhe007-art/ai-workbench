"""Data models for the LLM provider layer (Phase Beta-LLM)."""

from __future__ import annotations

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
    """A single conversation message."""

    role: LLMRole | str
    content: str
    name: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "role": self.role.value if isinstance(self.role, LLMRole) else str(self.role),
            "content": self.content,
        }
        if self.name:
            data["name"] = self.name
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMMessage":
        raw_role = data.get("role", "user")
        try:
            role: LLMRole | str = LLMRole(str(raw_role))
        except ValueError:
            role = str(raw_role)
        return cls(
            role=role,
            content=str(data.get("content", "")),
            name=str(data.get("name", "")),
        )


@dataclass
class LLMResponse:
    """Normalized provider response."""

    content: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
            "finish_reason": self.finish_reason,
            "metadata": self.metadata,
        }


def normalize_messages(messages: list[LLMMessage | dict[str, Any]]) -> list[LLMMessage]:
    """Accept either LLMMessage objects or plain dicts from callers."""
    normalized: list[LLMMessage] = []
    for message in messages or []:
        if isinstance(message, LLMMessage):
            normalized.append(message)
        elif isinstance(message, dict):
            normalized.append(LLMMessage.from_dict(message))
        else:
            raise TypeError(f"Unsupported message type: {type(message).__name__}")
    return normalized
