"""Prompt Manager - Phase 5.11"""
from app.prompts.registry import get_prompt_registry, PromptRegistry
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PromptManager:
    """High-level manager for prompt operations."""

    def __init__(self, registry: PromptRegistry | None = None):
        self._registry = registry or get_prompt_registry()

    def create_prompt(self, name: str, content: str, variables: list[str] | None = None, description: str = "") -> dict:
        template = self._registry.create(name, content, variables, description)
        return template.to_dict()

    def get_prompt(self, name: str, version: int | None = None) -> dict | None:
        template = self._registry.get(name, version)
        return template.to_dict() if template else None

    def list_prompts(self) -> list[dict]:
        return self._registry.list_all()

    def activate_version(self, name: str, version: int) -> bool:
        return self._registry.activate_version(name, version)

    def rollback(self, name: str) -> bool:
        return self._registry.rollback(name)

    def render(self, name: str, **kwargs) -> str:
        return self._registry.render(name, **kwargs)

    def get_registry(self) -> PromptRegistry:
        return self._registry


_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    global _manager
    if _manager is None:
        _manager = PromptManager()
    return _manager
