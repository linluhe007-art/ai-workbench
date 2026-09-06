"""
OpenAPI data models: APIKey, WebhookSubscription.
Phase 4.24: Open Platform API Layer.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WebhookEventType(str, Enum):
    """Supported webhook event types."""
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    ARTIFACT_CREATED = "artifact.created"
    AGENT_FAILED = "agent.failed"


@dataclass
class APIKey:
    """An API key for external clients."""
    id: str = field(default_factory=lambda: "apikey-" + uuid.uuid4().hex[:12])
    name: str = ""
    key_prefix: str = ""  # First 8 chars of raw key for display
    key_hash: str = ""  # SHA-256 hash of the full key
    permissions: list[str] = field(default_factory=list)
    tenant_id: str = ""
    created_by: str = ""
    enabled: bool = True
    last_used_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "key_prefix": self.key_prefix,
            "permissions": self.permissions,
            "tenant_id": self.tenant_id,
            "enabled": self.enabled,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class WebhookSubscription:
    """A webhook subscription for event delivery."""
    id: str = field(default_factory=lambda: "wh-" + uuid.uuid4().hex[:12])
    url: str = ""
    events: list[str] = field(default_factory=list)
    secret: str = ""  # HMAC signing secret
    tenant_id: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_delivery_at: datetime | None = None
    delivery_count: int = 0
    failure_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "events": self.events,
            "tenant_id": self.tenant_id,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_delivery_at": self.last_delivery_at.isoformat() if self.last_delivery_at else None,
            "delivery_count": self.delivery_count,
            "failure_count": self.failure_count,
        }