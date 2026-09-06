"""
ExperienceEngine - Closed-loop experience learning system.
Phase 4.23: Records task outcomes, learns from successes/failures,
provides statistics and recommendations.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.memory.experience import ExperienceMemory, ExperienceRecord
from app.memory.retrieval import MemoryRetriever
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExperienceStats:
    """Aggregated experience statistics."""
    total_records: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    top_patterns: list[dict] = field(default_factory=list)
    top_agents: list[dict] = field(default_factory=list)
    recent_failures: list[dict] = field(default_factory=list)


@dataclass
class FeedbackRecord:
    """User-provided feedback on a task execution."""
    task_id: str = ""
    task_pattern: str = ""
    rating: float = 0.0
    comment: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExperienceEngine:
    """
    Orchestrates experience recording, retrieval, and statistics.

    Responsibilities:
    - record_experience: Save task outcomes (auto-called by TaskRuntime)
    - record_failure: Save failure cases with error details
    - get_stats: Aggregated success/failure/pattern stats
    - query: Search historical experiences
    - record_feedback: User-provided feedback
    - get_recommendations: Agent/path recommendations for a task pattern
    """

    def __init__(self, experience_memory: ExperienceMemory | None = None):
        self._memory = experience_memory or ExperienceMemory()
        self._retriever = MemoryRetriever(
            keyword_weight=0.4,
            success_weight=0.3,
            decay_weight=0.3,
        )
        self._feedback: list[FeedbackRecord] = []

    # -- Recording --

    def record_experience(
        self,
        task_pattern: str,
        agents: list[str],
        success: bool,
        duration_ms: int = 0,
        metadata: dict | None = None,
    ) -> ExperienceRecord:
        """Record a task execution result."""
        meta = metadata or {}
        meta["duration_ms"] = duration_ms
        record = self._memory.record_experience(
            task_pattern=task_pattern,
            agents=agents,
            result=success,
            metadata=meta,
        )
        level = "success" if success else "failure"
        logger.info(
            "Experience recorded",
            pattern=task_pattern,
            result=level,
            agents=agents,
        )
        return record

    def record_failure(
        self,
        task_pattern: str,
        agents: list[str],
        error: str,
        duration_ms: int = 0,
    ) -> ExperienceRecord:
        """Record a failed task execution with error details."""
        return self.record_experience(
            task_pattern=task_pattern,
            agents=agents,
            success=False,
            duration_ms=duration_ms,
            metadata={"error": error, "failure_type": "execution"},
        )

    def record_feedback(
        self,
        task_id: str,
        task_pattern: str,
        rating: float,
        comment: str = "",
    ) -> FeedbackRecord:
        """Record user feedback on a task execution."""
        fb = FeedbackRecord(
            task_id=task_id,
            task_pattern=task_pattern,
            rating=max(0.0, min(10.0, rating)),
            comment=comment,
        )
        self._feedback.append(fb)
        logger.info("Feedback recorded", task_id=task_id, rating=rating)
        return fb

    # -- Querying --

    def query(
        self,
        task_pattern: str,
        limit: int = 10,
    ) -> list[dict]:
        """Search historical experiences by task pattern."""
        return self._memory.query_experience(task_pattern, limit=limit)

    def search(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict]:
        """Full-text search across all experiences using MemoryRetriever."""
        all_records = [
            {
                "task_pattern": r.task_pattern,
                "text": r.task_pattern,
                "success": r.success,
                "created_at": r.created_at.isoformat(),
                "source": "experience",
                "agents": r.agents,
                "metadata": r.metadata,
            }
            for r in self._memory._records
        ]
        results = self._retriever.retrieve(query, all_records, limit=limit)
        return [
            {
                **r.item,
                "score": r.score,
            }
            for r in results
        ]

    # -- Statistics --

    def get_stats(self) -> ExperienceStats:
        """Get aggregated experience statistics."""
        records = self._memory._records
        total = len(records)
        success_count = sum(1 for r in records if r.success)
        failure_count = total - success_count

        # Top patterns by frequency
        pattern_counts: dict[str, int] = {}
        for r in records:
            pattern_counts[r.task_pattern] = pattern_counts.get(r.task_pattern, 0) + 1
        top_patterns = sorted(
            pattern_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
        top_patterns_list = [
            {"pattern": p, "count": c, "success_rate": self._memory.get_success_rate(p)}
            for p, c in top_patterns
        ]

        # Top agents
        agent_totals: dict[str, tuple[int, int]] = {}
        for r in records:
            for aid in r.agents:
                st, tt = agent_totals.get(aid, (0, 0))
                agent_totals[aid] = (st + (1 if r.success else 0), tt + 1)
        top_agents = sorted(
            agent_totals.items(),
            key=lambda x: x[1][0] / x[1][1] if x[1][1] > 0 else 0,
            reverse=True,
        )[:10]
        top_agents_list = [
            {"agent_id": aid, "success_rate": s / t if t > 0 else 0, "total": t}
            for aid, (s, t) in top_agents
        ]

        # Recent failures
        failures = [r for r in records if not r.success]
        failures.sort(key=lambda r: r.created_at, reverse=True)
        recent_failures = [
            {
                "task_pattern": r.task_pattern,
                "agents": r.agents,
                "error": r.metadata.get("error", ""),
                "created_at": r.created_at.isoformat(),
            }
            for r in failures[:10]
        ]

        return ExperienceStats(
            total_records=total,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=success_count / total if total > 0 else 0.0,
            top_patterns=top_patterns_list,
            top_agents=top_agents_list,
            recent_failures=recent_failures,
        )

    def get_recommendations(
        self,
        task_pattern: str,
    ) -> dict:
        """Get agent/path recommendations for a task pattern."""
        best_agents = self._memory.get_best_agents(task_pattern)
        success_rate = self._memory.get_success_rate(task_pattern)
        similar = self._memory.query_experience(task_pattern, limit=5)

        warnings: list[str] = []
        for rec in similar:
            if not rec["success"]:
                err = rec.get("metadata", {}).get("error", "")
                if err:
                    warnings.append(f"Previous failure: {err}")

        return {
            "task_pattern": task_pattern,
            "recommended_agents": best_agents,
            "historical_success_rate": round(success_rate, 3),
            "similar_experiences_count": len(similar),
            "warnings": warnings,
        }

    # -- Feedback stats --

    def get_feedback_stats(self) -> dict:
        """Get aggregated feedback statistics."""
        if not self._feedback:
            return {"total": 0, "average_rating": 0.0, "ratings": []}
        avg = sum(f.rating for f in self._feedback) / len(self._feedback)
        return {
            "total": len(self._feedback),
            "average_rating": round(avg, 2),
            "ratings": [
                {"task_id": f.task_id, "pattern": f.task_pattern, "rating": f.rating}
                for f in self._feedback[-10:]
            ],
        }

    @property
    def memory(self) -> ExperienceMemory:
        return self._memory

    @property
    def retriever(self) -> MemoryRetriever:
        return self._retriever