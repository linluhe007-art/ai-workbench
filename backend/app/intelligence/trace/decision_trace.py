"""Decision Trace Model - Phase 5.11"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TraceType(str, Enum):
    COMMAND_ANALYSIS = "command_analysis"
    PLAN_GENERATION = "plan_generation"
    MEMORY_RETRIEVAL = "memory_retrieval"
    AGENT_SELECTION = "agent_selection"
    WORKFLOW_SELECTION = "workflow_selection"
    TOOL_SELECTION = "tool_selection"
    FINAL_RESULT = "final_result"


@dataclass
class DecisionTrace:
    """Records every key AI decision with full context."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    task_id: str = ""
    trace_type: str = ""
    component: str = ""
    input_data: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)
    reason: str = ""
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_id": self.task_id,
            "trace_type": self.trace_type,
            "component": self.component,
            "input_data": self.input_data,
            "decision": self.decision,
            "reason": self.reason,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def create(
        cls,
        trace_type: str,
        component: str,
        input_data: dict,
        decision: dict,
        reason: str = "",
        confidence: float = 0.0,
        task_id: str = "",
        user_id: str = "",
        metadata: dict | None = None,
    ) -> "DecisionTrace":
        return cls(
            trace_type=trace_type,
            component=component,
            input_data=input_data,
            decision=decision,
            reason=reason,
            confidence=confidence,
            task_id=task_id,
            user_id=user_id,
            metadata=metadata or {},
        )
