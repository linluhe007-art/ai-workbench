"""Optimization Engine - Phase 5.8"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.improvement.analyzer import AnalysisReport
from app.improvement.strategy import StrategyPlan, StrategyRecommendation
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationRecord:
    """Record of an applied optimization."""
    id: str = ""
    recommendation_id: str = ""
    category: str = ""
    title: str = ""
    action: dict = field(default_factory=dict)
    status: str = "applied"  # applied, reverted, pending
    applied_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recommendation_id": self.recommendation_id,
            "category": self.category,
            "title": self.title,
            "action": self.action,
            "status": self.status,
            "applied_at": self.applied_at,
            "result": self.result,
        }


class OptimizationEngine:
    """Applies and tracks optimization recommendations."""

    def __init__(self):
        self._records: dict[str, OptimizationRecord] = {}
        self._applied_count: dict[str, int] = {}

    def apply(self, recommendation: StrategyRecommendation) -> OptimizationRecord:
        rec_id = str(uuid.uuid4())
        record = OptimizationRecord(
            id=rec_id,
            recommendation_id=recommendation.id,
            category=recommendation.category,
            title=recommendation.title,
            action=recommendation.action,
        )
        self._records[rec_id] = record
        self._applied_count[recommendation.category] = self._applied_count.get(recommendation.category, 0) + 1
        logger.info("Optimization applied", id=rec_id, category=recommendation.category)
        return record

    def apply_plan(self, plan: StrategyPlan) -> list[OptimizationRecord]:
        records = []
        for rec in plan.recommendations:
            records.append(self.apply(rec))
        return records

    def get_record(self, record_id: str) -> OptimizationRecord | None:
        return self._records.get(record_id)

    def list_records(self) -> list[dict]:
        return sorted(
            [r.to_dict() for r in self._records.values()],
            key=lambda r: r["applied_at"],
            reverse=True,
        )

    def revert(self, record_id: str) -> bool:
        record = self._records.get(record_id)
        if record and record.status == "applied":
            record.status = "reverted"
            logger.info("Optimization reverted", id=record_id)
            return True
        return False

    def get_stats(self) -> dict:
        return {
            "total_applied": len(self._records),
            "by_category": self._applied_count,
        }


_engine: OptimizationEngine | None = None


def get_optimization_engine() -> OptimizationEngine:
    global _engine
    if _engine is None:
        _engine = OptimizationEngine()
    return _engine
