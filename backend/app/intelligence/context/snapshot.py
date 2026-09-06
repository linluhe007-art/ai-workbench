"""Context Snapshot - Phase 5.11"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ContextSnapshot:
    """Full AI context snapshot for debug and replay."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    user_input: str = ""
    memory_context: dict = field(default_factory=dict)
    knowledge_context: dict = field(default_factory=dict)
    plan: dict = field(default_factory=dict)
    agent: str = ""
    prompt: str = ""
    model: str = ""
    result: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "task_id": self.task_id, "user_input": self.user_input,
            "memory_context": self.memory_context, "knowledge_context": self.knowledge_context,
            "plan": self.plan, "agent": self.agent, "prompt": self.prompt,
            "model": self.model, "result": self.result, "created_at": self.created_at,
        }


class SnapshotStore:
    """Stores context snapshots keyed by task_id."""

    def __init__(self):
        self._snapshots: dict[str, ContextSnapshot] = {}

    def save(self, snapshot: ContextSnapshot):
        self._snapshots[snapshot.task_id] = snapshot

    def get(self, task_id: str) -> ContextSnapshot | None:
        return self._snapshots.get(task_id)

    def delete(self, task_id: str) -> bool:
        return self._snapshots.pop(task_id, None) is not None

    def list_task_ids(self) -> list[str]:
        return list(self._snapshots.keys())


_snapshot_store: SnapshotStore | None = None


def get_snapshot_store() -> SnapshotStore:
    global _snapshot_store
    if _snapshot_store is None:
        _snapshot_store = SnapshotStore()
    return _snapshot_store
