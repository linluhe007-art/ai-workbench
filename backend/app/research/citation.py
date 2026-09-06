"""Citation System - Phase Beta-Search

Tracks and manages source citations for research-generated content.
Every research artifact must include citations.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Citation:
    """A single source citation."""
    url: str
    title: str = ""
    access_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_hash: str = ""
    source_type: str = "web"
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.content_hash and self.url:
            self.content_hash = hashlib.sha256(self.url.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "access_date": self.access_date,
            "content_hash": self.content_hash,
            "source_type": self.source_type,
            "metadata": self.metadata,
        }


class CitationManager:
    """Manages citations for research artifacts."""

    def __init__(self):
        self._citations: dict[str, list[Citation]] = {}

    def record(self, task_id: str, citation: Citation):
        if task_id not in self._citations:
            self._citations[task_id] = []
        self._citations[task_id].append(citation)

    def record_batch(self, task_id: str, citations: list[Citation]):
        for c in citations:
            self.record(task_id, c)

    def get_citations(self, task_id: str) -> list[dict]:
        citations = self._citations.get(task_id, [])
        return [c.to_dict() for c in citations]

    def get_citation_count(self, task_id: str) -> int:
        return len(self._citations.get(task_id, []))

    def clear(self, task_id: str):
        self._citations.pop(task_id, None)

    def create_citation_from_source(self, title: str, url: str, source_type: str = "web") -> Citation:
        return Citation(url=url, title=title, source_type=source_type)


_citation_manager: CitationManager | None = None


def get_citation_manager() -> CitationManager:
    global _citation_manager
    if _citation_manager is None:
        _citation_manager = CitationManager()
    return _citation_manager
