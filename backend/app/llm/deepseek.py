"""DeepSeek and OpenAI-compatible LLM providers (Phase Beta-LLM)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.llm.errors import (
    LLMAuthError,
    LLMNotConfiguredError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.llm.models import LLMResponse, normalize_messages
from app.llm.provider import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Base provider for OpenAI-compatible chat completions APIs."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-chat",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds

    def get_model_name(self) -> str:
        return self.default_model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        messages,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        **kwargs: Any,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMNotConfiguredError(
                message="DeepSeek API Key is not configured",
                details={"provider": self.__class__.__name__},
            )

        normalized = normalize_messages(messages)
        payload: dict[str, Any] = {
            "model": model or self.default_model,
            "messages": [m.to_dict() for m in normalized],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if kwargs.get("stop"):
            payload["stop"] = kwargs["stop"]
        if kwargs.get("top_p") is not None:
            payload["top_p"] = kwargs["top_p"]

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }
        url = self.base_url + "/chat/completions"
        started = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                message="LLM provider request timed out",
                details={"provider": self.__class__.__name__},
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                message="LLM provider request failed",
                details={"error": str(exc), "provider": self.__class__.__name__},
            ) from exc

        latency_ms = round((time.monotonic() - started) * 1000, 1)

        if response.status_code in (401, 403):
            raise LLMAuthError(
                message="LLM API key is invalid or unauthorized",
                details={"status_code": response.status_code},
            )
        if response.status_code == 429:
            raise LLMRateLimitError(
                message="LLM provider rate limit exceeded",
                details={"status_code": response.status_code},
            )
        if response.status_code >= 400:
            raise LLMProviderError(
                message="LLM provider returned HTTP " + str(response.status_code),
                details={"status_code": response.status_code, "body": response.text[:500]},
            )

        try:
            data = response.json()
        except Exception as exc:
            raise LLMProviderError(
                message="LLM provider returned invalid JSON",
                details={"body": response.text[:500]},
            ) from exc

        try:
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content") or ""
            usage = data.get("usage", {}) or {}
            return LLMResponse(
                content=content,
                model=data.get("model") or (model or self.default_model),
                input_tokens=int(usage.get("prompt_tokens", 0)),
                output_tokens=int(usage.get("completion_tokens", 0)),
                latency_ms=latency_ms,
                finish_reason=choice.get("finish_reason") or "stop",
                metadata={"provider": self.__class__.__name__, "raw_model": data.get("model", "")},
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                message="LLM provider response is missing required fields",
                details={"body": str(data)[:500]},
            ) from exc


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek provider using the OpenAI-compatible chat completions API."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-chat",
        timeout_seconds: float = 60.0,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            timeout_seconds=timeout_seconds,
        )


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider using the official OpenAI chat completions API."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o-mini",
        timeout_seconds: float = 60.0,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            timeout_seconds=timeout_seconds,
        )
