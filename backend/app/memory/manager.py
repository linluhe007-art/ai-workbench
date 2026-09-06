"""
MemoryManager - Personal Long-term Memory.
Phase 5.3: Save, search, update, forget memories with PROFILE/PREFERENCE/PROJECT/KNOWLEDGE/EXPERIENCE types.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryType(str, Enum):
    PROFILE = "profile"
    PREFERENCE = "preference"
    PROJECT = "project"
    KNOWLEDGE = "knowledge"
    EXPERIENCE = "experience"


@dataclass
class MemoryRecord:
    """A single memory record for long-term storage."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    memory_type: MemoryType = MemoryType.KNOWLEDGE
    content: str = ""
    importance: float = 0.5
    embedding_id: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "importance": self.importance,
            "embedding_id": self.embedding_id,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MemoryManager:
    """
    Central memory management system.
    Supports:
    - save_memory(content, type, importance, tags)
    - search_memory(query, type, tags, limit)
    - update_memory(memory_id, updates)
    - forget_memory(memory_id)
    - get_by_type(memory_type)
    - get_profile / get_preferences helpers
    """

    def __init__(self, user_id: str = ""):
        self._user_id = user_id
        self._memories: dict[str, MemoryRecord] = {}
        self._type_index: dict[str, set[str]] = {t.value: set() for t in MemoryType}
        self._tag_index: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def save_memory(
        self,
        content: str,
        memory_type: str | MemoryType = MemoryType.KNOWLEDGE,
        importance: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        embedding_id: str = "",
    ) -> MemoryRecord:
        """Save a new memory record."""
        if isinstance(memory_type, str):
            memory_type = MemoryType(memory_type)

        record = MemoryRecord(
            user_id=self._user_id,
            memory_type=memory_type,
            content=content,
            importance=max(0.0, min(1.0, importance)),
            embedding_id=embedding_id,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._memories[record.id] = record
        self._type_index[memory_type.value].add(record.id)

        for tag in record.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(record.id)

        logger.info("Memory saved", id=record.id, type=memory_type.value, importance=record.importance)
        return record

    def search_memory(
        self,
        query: str = "",
        memory_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
        min_importance: float = 0.0,
    ) -> list[dict]:
        """Search memories by query, type, tags, and importance."""
        candidates = set(self._memories.keys())

        # Filter by type
        if memory_type:
            candidates &= self._type_index.get(memory_type, set())

        # Filter by tags (intersection of all tags)
        if tags:
            for tag in tags:
                candidates &= self._tag_index.get(tag, set())

        results = []
        query_lower = query.lower() if query else ""

        for mid in candidates:
            record = self._memories[mid]

            # Filter by importance
            if record.importance < min_importance:
                continue

            # Calculate relevance score
            score = self._calculate_relevance(record, query_lower)
            if query and score == 0:
                continue

            results.append((score, record))

        # Sort by (relevance, importance, recency)
        results.sort(key=lambda x: (x[0], x[1].importance, x[1].created_at), reverse=True)

        return [r[1].to_dict() for r in results[:limit]]

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        importance: float | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict | None:
        """Update an existing memory record."""
        record = self._memories.get(memory_id)
        if not record:
            return None

        # Remove old tag index entries
        for tag in record.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(memory_id)

        if content is not None:
            record.content = content
        if importance is not None:
            record.importance = max(0.0, min(1.0, importance))
        if tags is not None:
            record.tags = tags
        if metadata is not None:
            record.metadata = {**record.metadata, **metadata}

        # Re-index tags
        for tag in record.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(memory_id)

        record.updated_at = datetime.now(timezone.utc).isoformat()

        logger.info("Memory updated", id=memory_id)
        return record.to_dict()

    def forget_memory(self, memory_id: str) -> bool:
        """Delete a memory record."""
        record = self._memories.pop(memory_id, None)
        if not record:
            return False

        # Remove from indexes
        self._type_index.get(record.memory_type.value, set()).discard(memory_id)
        for tag in record.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(memory_id)

        logger.info("Memory forgotten", id=memory_id)
        return True

    def get_memory(self, memory_id: str) -> dict | None:
        """Get a single memory by ID."""
        record = self._memories.get(memory_id)
        return record.to_dict() if record else None

    # ------------------------------------------------------------------
    # Type-specific helpers
    # ------------------------------------------------------------------

    def get_by_type(self, memory_type: str, limit: int = 50) -> list[dict]:
        """Get all memories of a given type."""
        return self.search_memory(memory_type=memory_type, limit=limit)

    def get_profile(self) -> list[dict]:
        """Get profile memories."""
        return self.get_by_type(MemoryType.PROFILE.value)

    def get_preferences(self) -> list[dict]:
        """Get preference memories."""
        return self.get_by_type(MemoryType.PREFERENCE.value)

    def get_projects(self) -> list[dict]:
        """Get project memories."""
        return self.get_by_type(MemoryType.PROJECT.value)

    def get_knowledge(self, query: str = "", limit: int = 20) -> list[dict]:
        """Get knowledge memories, optionally filtered by query."""
        return self.search_memory(query=query, memory_type=MemoryType.KNOWLEDGE.value, limit=limit)

    def get_experiences(self, query: str = "", limit: int = 20) -> list[dict]:
        """Get experience memories, optionally filtered by query."""
        return self.search_memory(query=query, memory_type=MemoryType.EXPERIENCE.value, limit=limit)

    def get_high_importance(self, threshold: float = 0.7, limit: int = 20) -> list[dict]:
        """Get highly important memories across all types."""
        return self.search_memory(min_importance=threshold, limit=limit)

    # ------------------------------------------------------------------
    # Stats & maintenance
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get memory statistics."""
        type_counts = {}
        for t in MemoryType:
            type_counts[t.value] = len(self._type_index.get(t.value, set()))

        return {
            "total_memories": len(self._memories),
            "by_type": type_counts,
            "total_tags": len(self._tag_index),
            "user_id": self._user_id,
        }

    def clear(self) -> None:
        """Clear all memories (for testing)."""
        self._memories.clear()
        for t in MemoryType:
            self._type_index[t.value].clear()
        self._tag_index.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_relevance(record: MemoryRecord, query_lower: str) -> float:
        """Calculate relevance score for a query."""
        if not query_lower:
            return record.importance  # No query: use importance as score

        score = 0.0

        # Content matching
        content_lower = record.content.lower()
        if query_lower in content_lower:
            score += 2.0
        else:
            query_words = set(query_lower.split())
            content_words = set(content_lower.split())
            overlap = query_words & content_words
            if overlap:
                score += len(overlap) / len(query_words)

        # Tag matching
        tag_lower = [t.lower() for t in record.tags]
        for qw in query_lower.split():
            if any(qw in t for t in tag_lower):
                score += 0.5

        # Metadata matching
        meta_str = " ".join(str(v) for v in record.metadata.values()).lower()
        if query_lower in meta_str:
            score += 0.5

        # Boost by importance
        score *= (1.0 + record.importance)

        return round(score, 4)


# ------------------------------------------------------------------
# Global instance
# ------------------------------------------------------------------

_memory_manager: MemoryManager | None = None


def get_memory_manager(user_id: str = "") -> MemoryManager:
    """Get or create the global MemoryManager singleton."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(user_id=user_id)
    return _memory_manager


def reset_memory_manager() -> None:
    """Reset the global MemoryManager (for testing)."""
    global _memory_manager
    _memory_manager = None
