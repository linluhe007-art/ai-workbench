"""AI Usage Metrics - Phase 5.11"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AIUsageRecord:
    """Records model usage: tokens, latency, cost."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model: str = ""
    provider: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    cost: float = 0.0
    task_id: str = ""
    agent_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "model": self.model, "provider": self.provider,
            "tokens_input": self.tokens_input, "tokens_output": self.tokens_output,
            "latency_ms": self.latency_ms, "cost": self.cost,
            "task_id": self.task_id, "agent_id": self.agent_id,
            "created_at": self.created_at,
        }


class AIUsageTracker:
    """Tracks and aggregates AI model usage."""

    def __init__(self):
        self._records: list[AIUsageRecord] = []

    def record(self, model: str, provider: str, tokens_input: int, tokens_output: int,
               latency_ms: float = 0.0, cost: float = 0.0, task_id: str = "", agent_id: str = ""):
        rec = AIUsageRecord(model=model, provider=provider, tokens_input=tokens_input,
                           tokens_output=tokens_output, latency_ms=latency_ms, cost=cost,
                           task_id=task_id, agent_id=agent_id)
        self._records.append(rec)
        return rec

    def get_records(self, limit: int = 100, offset: int = 0) -> list[dict]:
        sorted_recs = sorted(self._records, key=lambda r: r.created_at, reverse=True)
        return [r.to_dict() for r in sorted_recs[offset:offset + limit]]

    def get_summary(self) -> dict:
        total_input = sum(r.tokens_input for r in self._records)
        total_output = sum(r.tokens_output for r in self._records)
        total_cost = sum(r.cost for r in self._records)
        latencies = [r.latency_ms for r in self._records if r.latency_ms > 0]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        model_usage: dict[str, int] = {}
        for r in self._records:
            model_usage[r.model] = model_usage.get(r.model, 0) + 1

        return {
            "total_records": len(self._records),
            "total_tokens_input": total_input,
            "total_tokens_output": total_output,
            "total_tokens": total_input + total_output,
            "total_cost": round(total_cost, 4),
            "average_latency_ms": round(avg_latency, 1),
            "model_usage": model_usage,
        }

    def clear(self):
        self._records.clear()


_tracker: AIUsageTracker | None = None


def get_ai_usage_tracker() -> AIUsageTracker:
    global _tracker
    if _tracker is None:
        _tracker = AIUsageTracker()
    return _tracker
