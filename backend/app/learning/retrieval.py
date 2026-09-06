"""
ExperienceRetrieval - Specialized retrieval for experience records.
Phase 4.23: Wraps MemoryRetriever with experience-specific search,
keyword matching, and embedding interface placeholder.
"""
from dataclasses import dataclass, field
from typing import Any

from app.memory.experience import ExperienceMemory
from app.memory.retrieval import MemoryRetriever, RetrievalResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExperienceSearchResult:
    """A single search result from experience retrieval."""
    task_pattern: str
    score: float
    agents: list[str] = field(default_factory=list)
    success: bool = False
    created_at: str = ""
    metadata: dict = field(default_factory=dict)


class ExperienceRetrieval:
    """
    Experience-specific retrieval engine.

    Features:
    - keyword matching against task patterns
    - agent combination filtering
    - success/failure filtering
    - date range filtering
    - Embedding interface placeholder (for future vector search)
    """

    def __init__(self, experience_memory: ExperienceMemory | None = None):
        self._memory = experience_memory or ExperienceMemory()
        self._retriever = MemoryRetriever(
            keyword_weight=0.5,
            success_weight=0.3,
            decay_weight=0.2,
        )

    def search(
        self,
        query: str = "",
        filter_success: bool | None = None,
        filter_agents: list[str] | None = None,
        min_score: float = 0.0,
        limit: int = 20,
    ) -> list[ExperienceSearchResult]:
        """
        Search experiences with optional filters.

        Args:
            query: Search keywords
            filter_success: True=only successes, False=only failures, None=all
            filter_agents: Only include experiences using these agents
            min_score: Minimum relevance score (0-1)
            limit: Max results
        """
        all_records = self._memory._records

        # Apply filters
        filtered = []
        for r in all_records:
            if filter_success is not None and r.success != filter_success:
                continue
            if filter_agents and not any(a in r.agents for a in filter_agents):
                continue
            filtered.append({
                "text": r.task_pattern,
                "task_pattern": r.task_pattern,
                "success": r.success,
                "created_at": r.created_at.isoformat(),
                "source": "experience",
                "agents": r.agents,
                "metadata": r.metadata,
            })

        if query:
            results = self._retriever.retrieve(query, filtered, limit=limit)
        else:
            results = [
                RetrievalResult(item=r, score=1.0, source="experience")
                for r in filtered
            ]

        output = []
        for r in results:
            if r.score < min_score:
                continue
            output.append(ExperienceSearchResult(
                task_pattern=r.item.get("task_pattern", ""),
                score=r.score,
                agents=r.item.get("agents", []),
                success=r.item.get("success", False),
                created_at=r.item.get("created_at", ""),
                metadata=r.item.get("metadata", {}),
            ))
            if len(output) >= limit:
                break

        return output

    def find_similar(
        self,
        task_pattern: str,
        limit: int = 5,
    ) -> list[ExperienceSearchResult]:
        """Find experiences similar to a given task pattern."""
        return self.search(query=task_pattern, limit=limit)

    def get_embedding_placeholder(self, text: str) -> list[float]:
        """
        Placeholder for future embedding-based retrieval.
        Currently returns a simple hash-based vector.
        Replace with real embedding model (e.g., text-embedding-3-small) when needed.
        """
        # Simple hash-based placeholder
        h = hash(text) if text else 0
        return [(h >> (i * 8)) & 0xFF / 255.0 for i in range(8)]