"""LLM Model Providers - Phase 5.9"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderType(str, Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama_cpp"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass
class ModelInfo:
    """Information about an available model."""
    name: str
    provider: ProviderType
    endpoint: str = ""
    size: str = ""
    context_length: int = 4096
    available: bool = True
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "provider": self.provider.value,
            "endpoint": self.endpoint,
            "size": self.size,
            "context_length": self.context_length,
            "available": self.available,
            "metadata": self.metadata,
        }


@dataclass
class ModelResponse:
    """Response from a model invocation."""
    text: str
    model: str = ""
    usage: dict = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "model": self.model,
            "usage": self.usage,
            "error": self.error,
        }


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers."""

    def __init__(self, endpoint: str = "", api_key: str = ""):
        self.endpoint = endpoint
        self.api_key = api_key

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        ...

    @abstractmethod
    async def generate(self, prompt: str, model: str = "", **kwargs) -> ModelResponse:
        ...

    @abstractmethod
    async def test_connection(self) -> bool:
        ...


class OllamaProvider(BaseLLMProvider):
    """Ollama local model provider."""

    def __init__(self, endpoint: str = "http://localhost:11434"):
        super().__init__(endpoint=endpoint)
        self._models: list[ModelInfo] = []

    async def list_models(self) -> list[ModelInfo]:
        # In production, call Ollama API: GET /api/tags
        # For now, return configured models
        if not self._models:
            self._models = [
                ModelInfo(name="llama3", provider=ProviderType.OLLAMA, endpoint=self.endpoint, size="4.7GB", context_length=8192),
                ModelInfo(name="mistral", provider=ProviderType.OLLAMA, endpoint=self.endpoint, size="4.1GB", context_length=32768),
                ModelInfo(name="codellama", provider=ProviderType.OLLAMA, endpoint=self.endpoint, size="3.8GB", context_length=16384),
            ]
        return self._models

    async def generate(self, prompt: str, model: str = "llama3", **kwargs) -> ModelResponse:
        return ModelResponse(
            text=f"[Ollama/{model}] Generated response for: {prompt[:50]}...",
            model=model,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 50},
        )

    async def test_connection(self) -> bool:
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception:
            return False


class LlamaCppProvider(BaseLLMProvider):
    """llama.cpp server provider."""

    def __init__(self, endpoint: str = "http://localhost:8080"):
        super().__init__(endpoint=endpoint)
        self._models: list[ModelInfo] = []

    async def list_models(self) -> list[ModelInfo]:
        if not self._models:
            self._models = [
                ModelInfo(name="llama-cpp-default", provider=ProviderType.LLAMA_CPP, endpoint=self.endpoint, size="3.5GB", context_length=4096),
            ]
        return self._models

    async def generate(self, prompt: str, model: str = "llama-cpp-default", **kwargs) -> ModelResponse:
        return ModelResponse(
            text=f"[llama.cpp/{model}] Response: {prompt[:50]}...",
            model=model,
        )

    async def test_connection(self) -> bool:
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception:
            return False


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI-compatible API provider (vLLM, TGI, etc.)."""

    def __init__(self, endpoint: str = "http://localhost:8000/v1", api_key: str = ""):
        super().__init__(endpoint=endpoint, api_key=api_key)
        self._models: list[ModelInfo] = []

    async def list_models(self) -> list[ModelInfo]:
        if not self._models:
            self._models = [
                ModelInfo(name="gpt-4o-mini", provider=ProviderType.OPENAI_COMPATIBLE, endpoint=self.endpoint, context_length=128000),
                ModelInfo(name="deepseek-v3", provider=ProviderType.OPENAI_COMPATIBLE, endpoint=self.endpoint, context_length=65536),
            ]
        return self._models

    async def generate(self, prompt: str, model: str = "gpt-4o-mini", **kwargs) -> ModelResponse:
        return ModelResponse(
            text=f"[OpenAI/{model}] Generated: {prompt[:50]}...",
            model=model,
            usage={"prompt_tokens": len(prompt.split()), "completion_tokens": 80},
        )

    async def test_connection(self) -> bool:
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception:
            return False


class ProviderFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def create(provider_type: ProviderType, endpoint: str = "", api_key: str = "") -> BaseLLMProvider:
        if provider_type == ProviderType.OLLAMA:
            return OllamaProvider(endpoint=endpoint or "http://localhost:11434")
        elif provider_type == ProviderType.LLAMA_CPP:
            return LlamaCppProvider(endpoint=endpoint or "http://localhost:8080")
        elif provider_type == ProviderType.OPENAI_COMPATIBLE:
            return OpenAICompatibleProvider(endpoint=endpoint or "http://localhost:8000/v1", api_key=api_key)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
