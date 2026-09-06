"""
Audit & Execution Explainability module.

Provides:
- AuditRecord: structured audit event
- AuditLogger: in-memory audit log with query support
- Integration hooks for TaskEventStore, RequestIDMiddleware, AppRuntime
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AuditRecord:
    """A single audit event recording a key action in the system."""

    id: str
    timestamp: datetime
    actor: str
    action: str
    resource_type: str
    resource_id: str
    task_id: str | None = None
    request_id: str | None = None
    before: dict = field(default_factory=dict)
    after: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "task_id": self.task_id,
            "request_id": self.request_id,
            "before": self.before,
            "after": self.after,
            "metadata": self.metadata,
        }


class AuditLogger:
    """
    In-memory audit log with query support.

    Records all key actions across the system.
    Integrates with TaskEventStore and RequestIDMiddleware.
    """

    def __init__(self, max_records: int = 10000):
        self._records: list[AuditRecord] = []
        self._max_records = max_records

    def record(
        self,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        task_id: str | None = None,
        request_id: str | None = None,
        before: dict | None = None,
        after: dict | None = None,
        metadata: dict | None = None,
    ) -> AuditRecord:
        """Record a new audit event."""
        record = AuditRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            task_id=task_id,
            request_id=request_id,
            before=before or {},
            after=after or {},
            metadata=metadata or {},
        )
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]
        return record

    def query(
        self,
        task_id: str | None = None,
        actor: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        request_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditRecord], int]:
        """
        Query audit records with optional filters.

        Returns (records, total_count).
        """
        results = self._records

        if task_id is not None:
            results = [r for r in results if r.task_id == task_id]
        if actor is not None:
            results = [r for r in results if r.actor == actor]
        if action is not None:
            results = [r for r in results if r.action == action]
        if resource_type is not None:
            results = [r for r in results if r.resource_type == resource_type]
        if resource_id is not None:
            results = [r for r in results if r.resource_id == resource_id]
        if request_id is not None:
            results = [r for r in results if r.request_id == request_id]
        if since is not None:
            results = [r for r in results if r.timestamp >= since]
        if until is not None:
            results = [r for r in results if r.timestamp <= until]

        total = len(results)
        paginated = results[offset:offset + limit]
        return paginated, total

    def get_audit_trail(self, task_id: str) -> list[AuditRecord]:
        """Get the full audit trail for a specific task, ordered by timestamp."""
        records, _ = self.query(task_id=task_id, limit=10000)
        return sorted(records, key=lambda r: r.timestamp)

    def get_agent_audit(self, agent_id: str, limit: int = 100) -> list[AuditRecord]:
        """Get audit records for a specific agent."""
        records, _ = self.query(actor=agent_id, limit=limit)
        return sorted(records, key=lambda r: r.timestamp)

    def get_resource_audit(self, resource_type: str, resource_id: str, limit: int = 100) -> list[AuditRecord]:
        """Get audit records for a specific resource."""
        records, _ = self.query(resource_type=resource_type, resource_id=resource_id, limit=limit)
        return sorted(records, key=lambda r: r.timestamp)

    def count(self) -> int:
        """Total number of audit records."""
        return len(self._records)

    def clear(self) -> None:
        """Clear all audit records."""
        self._records.clear()


# Global singleton
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger singleton."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def reset_audit_logger() -> None:
    """Reset the global audit logger (for testing)."""
    global _audit_logger
    _audit_logger = None