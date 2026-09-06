"""Provider factory for the LLM layer (Phase Beta-LLM)."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.deepseek import DeepSeekProvider, OpenAIProvider
from app.llm.provider import LLMProvider, MockLLMProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)

SUPPORTED_PROVIDERS = ("deepseek", "openai", "mock")


def create_llm_provider(
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout_seconds: float | None = None,
    settings: Settings | None = None,
) -> LLMProvider:
    """Create a provider instance from explicit args or application settings."""
    config = settings or get_settings()
    provider_name = (provider or config.llm_provider or "deepseek").lower()
    timeout = timeout_seconds if timeout_seconds is not None else config.llm_timeout_seconds

    if provider_name == "mock":
        return MockLLMProvider(default_model=model or config.llm_model or "mock-llm-v1")

    if provider_name == "deepseek":
        return DeepSeekProvider(
            api_key=api_key if api_key is not None else config.deepseek_api_key,
            base_url=base_url or config.deepseek_base_url or "https://api.deepseek.com",
            default_model=model or config.deepseek_model or config.llm_model or "deepseek-chat",
            timeout_seconds=timeout,
        )

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=api_key if api_key is not None else config.openai_api_key,
            base_url=base_url or config.openai_base_url or "https://api.openai.com/v1",
            default_model=model or config.openai_model or config.llm_model or "gpt-4o-mini",
            timeout_seconds=timeout,
        )

    logger.warning("Unknown LLM provider, falling back to mock", provider=provider_name)
    return MockLLMProvider(default_model=config.llm_model or "mock-llm-v1")


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Return the configured provider singleton."""
    return create_llm_provider(settings=settings)


def get_llm_config_info(settings: Settings | None = None) -> dict:
    """Return non-sensitive provider configuration for API responses."""
    config = settings or get_settings()
    provider = create_llm_provider(settings=config)
    provider_name = (config.llm_provider or "deepseek").lower()
    api_key_set = bool(config.deepseek_api_key or config.openai_api_key)
    configured = True if provider_name == "mock" else (provider.is_configured() and api_key_set)
    return {
        "provider": provider_name,
        "model": provider.get_model_name(),
        "configured": configured,
        "api_key_set": api_key_set,
        "supported_providers": list(SUPPORTED_PROVIDERS),
    }
