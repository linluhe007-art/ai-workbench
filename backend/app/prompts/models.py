"""Prompt Template Model - Phase 5.11"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class PromptTemplate:
    """Versioned prompt template."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    version: int = 1
    content: str = ""
    variables: list[str] = field(default_factory=list)
    description: str = ""
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "content": self.content,
            "variables": self.variables,
            "description": self.description,
            "active": self.active,
            "created_at": self.created_at,
        }

    def render(self, **kwargs) -> str:
        """Render the prompt template with variable substitution."""
        result = self.content
        for var_name in self.variables:
            placeholder = "{{" + var_name + "}}"
            value = kwargs.get(var_name, "")
            result = result.replace(placeholder, str(value))
        return result
