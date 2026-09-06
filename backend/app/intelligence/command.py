"""
CommandProcessor - Processes user commands end-to-end.
Phase 5.1: Wraps CommandRouter, adds history tracking, creates API response.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.intelligence.router import CommandRouter
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CommandResult:
    """Result of processing a user command."""
    intent: dict = field(default_factory=dict)
    task_id: str = ""
    classification: dict = field(default_factory=dict)
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "task_id": self.task_id,
            "classification": self.classification,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


class CommandProcessor:
    """
    High-level entry point for the intelligent command system.

    Usage:
        processor = CommandProcessor(router)
        result = await processor.process("help me research AI trends")
    """

    def __init__(self, router: CommandRouter | None = None):
        self._router = router or CommandRouter()
        self._history: list[dict] = []

    async def process(self, prompt: str, user_id: str = "") -> CommandResult:
        """
        Process a user command and return a structured result.

        Args:
            prompt: Natural language command
            user_id: Optional user identifier

        Returns:
            CommandResult with intent, task_id, confidence
        """
        routed = await self._router.route(prompt, user_id=user_id)

        result = CommandResult(
            intent=routed.get("intent", {}),
            task_id=routed.get("task_id", ""),
            classification=routed.get("classification", {}),
            confidence=routed.get("confidence", 0.0),
        )

        # Track history
        self._history.append({
            "prompt": prompt,
            "intent": routed.get("intent", {}),
            "task_id": routed.get("task_id", ""),
            "created_at": result.created_at,
        })

        logger.info("Command processed", task_id=result.task_id, task_type=routed.get("intent", {}).get("task_type"))
        return result

    def get_history(self, limit: int = 20) -> list[dict]:
        """Return recent command history."""
        return self._history[-limit:]

    def clear_history(self) -> None:
        """Clear command history."""
        self._history.clear()