"""Prompt Registry - Phase 5.11"""
from app.prompts.models import PromptTemplate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PromptRegistry:
    """Registry for managing prompt templates with versioning."""

    def __init__(self):
        self._prompts: dict[str, dict[int, PromptTemplate]] = {}
        self._active_versions: dict[str, int] = {}

    def create(self, name: str, content: str, variables: list[str] | None = None, description: str = "") -> PromptTemplate:
        if name not in self._prompts:
            self._prompts[name] = {}
            version = 1
        else:
            version = max(self._prompts[name].keys()) + 1

        template = PromptTemplate(
            name=name, version=version, content=content,
            variables=variables or [], description=description, active=True,
        )
        self._prompts[name][version] = template

        # Deactivate previous versions
        for v, t in self._prompts[name].items():
            if v != version:
                t.active = False

        self._active_versions[name] = version
        logger.info("Prompt created", name=name, version=version)
        return template

    def get(self, name: str, version: int | None = None) -> PromptTemplate | None:
        if name not in self._prompts:
            return None
        if version is not None:
            return self._prompts[name].get(version)
        active_ver = self._active_versions.get(name)
        if active_ver:
            return self._prompts[name].get(active_ver)
        return None

    def get_active(self, name: str) -> PromptTemplate | None:
        return self.get(name)

    def list_all(self) -> list[dict]:
        results = []
        for name, versions in self._prompts.items():
            for v, t in versions.items():
                results.append(t.to_dict())
        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results

    def list_names(self) -> list[str]:
        return list(self._prompts.keys())

    def activate_version(self, name: str, version: int) -> bool:
        if name not in self._prompts or version not in self._prompts[name]:
            return False
        for v, t in self._prompts[name].items():
            t.active = (v == version)
        self._active_versions[name] = version
        logger.info("Prompt version activated", name=name, version=version)
        return True

    def rollback(self, name: str) -> bool:
        if name not in self._prompts:
            return False
        current = self._active_versions.get(name, 0)
        if current <= 1:
            return False
        return self.activate_version(name, current - 1)

    def render(self, name: str, **kwargs) -> str:
        template = self.get_active(name)
        if template is None:
            return ""
        return template.render(**kwargs)


_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry
