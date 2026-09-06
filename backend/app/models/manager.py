"""Model Manager - Phase 5.9"""
from dataclasses import dataclass, field
from typing import Any

from app.models.provider import (
    BaseLLMProvider, ProviderType, ModelInfo, ProviderFactory,
)
from app.models.router import ModelRouter, get_model_router
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelConfig:
    """Configuration for a model provider."""
    provider_type: ProviderType
    endpoint: str = ""
    api_key: str = ""
    enabled: bool = True
    priority: int = 0  # Higher = more preferred

    def to_dict(self) -> dict:
        return {
            "provider_type": self.provider_type.value,
            "endpoint": self.endpoint,
            "api_key_set": bool(self.api_key),
            "enabled": self.enabled,
            "priority": self.priority,
        }


class ModelManager:
    """Manages model providers, configurations, and discovery."""

    def __init__(self, router: ModelRouter | None = None):
        self._router = router or get_model_router()
        self._configs: dict[ProviderType, ModelConfig] = {}
        self._test_results: dict[str, bool] = {}

    def configure(self, provider_type: ProviderType, endpoint: str = "", api_key: str = "", priority: int = 0):
        config = ModelConfig(provider_type=provider_type, endpoint=endpoint, api_key=api_key, priority=priority)
        self._configs[provider_type] = config

        # Update provider
        provider = ProviderFactory.create(provider_type, endpoint=endpoint, api_key=api_key)
        self._router.set_provider(provider_type, provider)
        logger.info("Model configured", provider=provider_type.value, endpoint=endpoint)

    def get_config(self, provider_type: ProviderType) -> ModelConfig | None:
        return self._configs.get(provider_type)

    def list_configs(self) -> list[dict]:
        return [c.to_dict() for c in self._configs.values()]

    async def discover_models(self, provider_type: ProviderType | None = None) -> list[ModelInfo]:
        """Discover available models from configured providers."""
        models: list[ModelInfo] = []
        providers_to_check = (
            [provider_type] if provider_type else list(ProviderType)
        )
        for pt in providers_to_check:
            provider = self._router.get_provider(pt)
            if not provider:
                continue
            try:
                pt_models = await provider.list_models()
                models.extend(pt_models)
            except Exception as e:
                logger.warning("Model discovery failed", provider=pt.value, error=str(e))
        return models

    async def test_provider(self, provider_type: ProviderType) -> bool:
        """Test connection to a provider."""
        provider = self._router.get_provider(provider_type)
        if not provider:
            self._test_results[provider_type.value] = False
            return False
        try:
            ok = await provider.test_connection()
            self._test_results[provider_type.value] = ok
            return ok
        except Exception as e:
            self._test_results[provider_type.value] = False
            logger.error("Provider test failed", provider=provider_type.value, error=str(e))
            return False

    async def test_all_providers(self) -> dict[str, bool]:
        """Test all configured providers."""
        results = {}
        for pt in self._configs:
            results[pt.value] = await self.test_provider(pt)
        return results

    def get_all_available_models(self) -> list[dict]:
        """Get all models from the routing table as available options."""
        routes = self._router.get_routing_table()
        models = []
        seen = set()
        for cat, decision in routes.items():
            if decision["model_name"] not in seen:
                seen.add(decision["model_name"])
                models.append({
                    "name": decision["model_name"],
                    "provider": decision["provider_type"],
                    "task_categories": [cat],
                    "privacy_level": decision["privacy_level"],
                    "estimated_cost": decision["estimated_cost"],
                })
        return models

    def get_router(self) -> ModelRouter:
        return self._router


_manager: ModelManager | None = None


def get_model_manager() -> ModelManager:
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager
