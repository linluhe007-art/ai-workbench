"""Model Router - Phase 5.9"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.models.provider import BaseLLMProvider, ProviderType, ProviderFactory


class TaskCategory(str, Enum):
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"
    ANALYSIS = "analysis"
    CHAT = "chat"
    PRIVATE = "private"


class PrivacyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    STRICT = "strict"


@dataclass
class RoutingDecision:
    """Result of model routing decision."""
    provider_type: ProviderType
    model_name: str
    reason: str
    privacy_level: PrivacyLevel = PrivacyLevel.LOW
    estimated_cost: str = "free"

    def to_dict(self) -> dict:
        return {
            "provider_type": self.provider_type.value,
            "model_name": self.model_name,
            "reason": self.reason,
            "privacy_level": self.privacy_level.value,
            "estimated_cost": self.estimated_cost,
        }


class ModelRouter:
    """Routes tasks to appropriate models based on task type, privacy, and cost."""

    # Default routing table: task_category -> (provider, model, privacy, cost)
    _routing_table: dict[str, tuple] = {
        TaskCategory.CODING: (ProviderType.OLLAMA, "codellama", PrivacyLevel.HIGH, "free"),
        TaskCategory.RESEARCH: (ProviderType.OPENAI_COMPATIBLE, "deepseek-v3", PrivacyLevel.MEDIUM, "low"),
        TaskCategory.WRITING: (ProviderType.OPENAI_COMPATIBLE, "gpt-4o-mini", PrivacyLevel.LOW, "low"),
        TaskCategory.ANALYSIS: (ProviderType.OLLAMA, "mistral", PrivacyLevel.HIGH, "free"),
        TaskCategory.CHAT: (ProviderType.OLLAMA, "llama3", PrivacyLevel.HIGH, "free"),
        TaskCategory.PRIVATE: (ProviderType.OLLAMA, "llama3", PrivacyLevel.STRICT, "free"),
    }

    def __init__(self):
        self._providers: dict[ProviderType, BaseLLMProvider] = {}
        self._custom_routes: dict[str, RoutingDecision] = {}

    def set_provider(self, provider_type: ProviderType, provider: BaseLLMProvider):
        self._providers[provider_type] = provider

    def get_provider(self, provider_type: ProviderType) -> BaseLLMProvider | None:
        return self._providers.get(provider_type)

    def add_custom_route(self, task_category: str, decision: RoutingDecision):
        self._custom_routes[task_category] = decision

    def route(self, task_category: str, privacy_level: PrivacyLevel | None = None) -> RoutingDecision:
        # Check custom routes first
        if task_category in self._custom_routes:
            return self._custom_routes[task_category]

        # Fall back to routing table
        if task_category in self._routing_table:
            provider_type, model, default_privacy, cost = self._routing_table[task_category]
            # If privacy requirement exceeds default, escalate to local model
            if privacy_level and privacy_level.value > default_privacy.value:
                provider_type = ProviderType.OLLAMA
                model = "llama3"
                cost = "free"
                reason = f"Privacy {privacy_level.value} requires local model"
            else:
                reason = f"Default route for {task_category}"
            return RoutingDecision(
                provider_type=provider_type,
                model_name=model,
                reason=reason,
                privacy_level=privacy_level or default_privacy,
                estimated_cost=cost,
            )

        # Default fallback
        return RoutingDecision(
            provider_type=ProviderType.OLLAMA,
            model_name="llama3",
            reason=f"No specific route for {task_category}, using default",
            privacy_level=PrivacyLevel.HIGH,
            estimated_cost="free",
        )

    def get_routing_table(self) -> dict:
        return {
            cat: RoutingDecision(
                provider_type=pt, model_name=mn, reason=f"Default route",
                privacy_level=pl, estimated_cost=ec,
            ).to_dict()
            for cat, (pt, mn, pl, ec) in self._routing_table.items()
        }

    async def generate(self, task_category: str, prompt: str, privacy_level: PrivacyLevel | None = None) -> dict:
        decision = self.route(task_category, privacy_level)
        provider = self._providers.get(decision.provider_type)
        if not provider:
            provider = ProviderFactory.create(decision.provider_type)
            self._providers[decision.provider_type] = provider

        response = await provider.generate(prompt, model=decision.model_name)
        return {
            "routing": decision.to_dict(),
            "response": response.to_dict(),
        }


_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
        # Initialize default providers
        _router.set_provider(ProviderType.OLLAMA, ProviderFactory.create(ProviderType.OLLAMA))
        _router.set_provider(ProviderType.LLAMA_CPP, ProviderFactory.create(ProviderType.LLAMA_CPP))
        _router.set_provider(ProviderType.OPENAI_COMPATIBLE, ProviderFactory.create(ProviderType.OPENAI_COMPATIBLE))
    return _router
