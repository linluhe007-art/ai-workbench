"""Decision Engine - Phase 5.10"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.os.context import UnifiedContext


@dataclass
class Decision:
    """A decision made by the AI OS about how to handle a user intent."""
    action: str = ""  # create_task, suggest, query, automate, improve, chat
    confidence: float = 0.0
    reasoning: str = ""
    task_description: str = ""
    recommended_agents: list[str] = field(default_factory=list)
    should_automate: bool = False
    should_learn: bool = False
    priority: int = 0  # 0=low, 1=medium, 2=high

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "task_description": self.task_description,
            "recommended_agents": self.recommended_agents,
            "should_automate": self.should_automate,
            "should_learn": self.should_learn,
            "priority": self.priority,
        }


class DecisionEngine:
    """Makes decisions about how to handle user intents based on context."""

    def decide(self, context: UnifiedContext) -> Decision:
        intent = context.user_intent.lower() if context.user_intent else ""

        # Determine action based on intent analysis
        action = self._classify_action(intent)
        confidence = self._calculate_confidence(context)
        reasoning = self._build_reasoning(context, action)

        # Build task description
        task_desc = intent if intent else "General inquiry"

        # Recommend agents
        agents = context.recommended_agents or []

        # Determine if this should be automated
        should_automate = self._should_automate(intent, context)

        # Determine if learning should happen
        should_learn = context.system_state.agents_available > 0

        # Priority based on context
        priority = self._determine_priority(intent, context)

        return Decision(
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            task_description=task_desc,
            recommended_agents=agents,
            should_automate=should_automate,
            should_learn=should_learn,
            priority=priority,
        )

    def _classify_action(self, intent: str) -> str:
        """Classify intent into an action."""
        task_keywords = ["analyze", "research", "write", "generate", "build", "create", "search", "study"]
        query_keywords = ["how", "what", "when", "where", "why", "explain", "tell", "show"]
        automate_keywords = ["every", "daily", "weekly", "schedule", "automate", "repeat"]
        improve_keywords = ["optimize", "improve", "better", "faster", "fix"]

        if any(kw in intent for kw in automate_keywords):
            return "automate"
        elif any(kw in intent for kw in improve_keywords):
            return "improve"
        elif any(kw in intent for kw in task_keywords):
            return "create_task"
        elif any(kw in intent for kw in query_keywords):
            return "query"
        elif not intent:
            return "suggest"
        else:
            return "chat"

    def _calculate_confidence(self, context: UnifiedContext) -> float:
        """Calculate decision confidence based on context richness."""
        score = 0.3  # Base confidence

        if context.user_intent:
            score += 0.2
        if context.memory_snapshot.recent_experiences:
            score += 0.1
        if context.recommended_agents:
            score += 0.15
        if context.system_state.agents_available > 0:
            score += 0.15
        if context.improvement_suggestions:
            score += 0.1

        return min(score, 1.0)

    def _build_reasoning(self, context: UnifiedContext, action: str) -> str:
        """Build human-readable reasoning."""
        parts = [f"Action: {action}."]
        if context.system_state.agents_available > 0:
            parts.append(f"{context.system_state.agents_available} agents available.")
        if context.memory_snapshot.recent_experiences:
            parts.append(f"{len(context.memory_snapshot.recent_experiences)} relevant memories found.")
        return " ".join(parts)

    def _should_automate(self, intent: str, context: UnifiedContext) -> bool:
        if any(kw in intent for kw in ["every", "daily", "weekly", "schedule"]):
            return True
        return context.system_state.automations_running > 0

    def _determine_priority(self, intent: str, context: UnifiedContext) -> int:
        if any(kw in intent for kw in ["urgent", "asap", "critical"]):
            return 2
        if context.improvement_suggestions:
            return 1
        return 0


_engine: DecisionEngine | None = None


def get_decision_engine() -> DecisionEngine:
    global _engine
    if _engine is None:
        _engine = DecisionEngine()
    return _engine
