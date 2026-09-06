"""
Memory Integration - Phase 5.3
Auto-reads long-term memory context before planning and agent execution.
"""

from app.memory.manager import MemoryManager, get_memory_manager, MemoryType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryIntegration:
    """
    Integrates MemoryManager with Planner and Agent execution.
    Provides automatic memory context injection.
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        self._mgr = memory_manager or get_memory_manager()

    def get_context_for_task(self, task: str, agent_type: str | None = None) -> dict:
        """
        Get relevant memory context for a task.
        Returns profile, preferences, and relevant knowledge/experience.
        """
        profile = self._mgr.get_profile()
        preferences = self._mgr.get_preferences()

        # Search relevant knowledge
        knowledge = self._mgr.get_knowledge(query=task, limit=10)

        # Search past experiences
        experiences = self._mgr.get_experiences(query=task, limit=5)

        context = {
            "profile": [p["content"] for p in profile[:3]],
            "preferences": [p["content"] for p in preferences[:3]],
            "relevant_knowledge": [
                {"content": k["content"], "tags": k.get("tags", []), "importance": k.get("importance", 0)}
                for k in knowledge[:5]
            ],
            "past_experiences": [
                {"content": e["content"], "tags": e.get("tags", []), "importance": e.get("importance", 0)}
                for e in experiences[:3]
            ],
        }

        logger.info(
            "Memory context loaded",
            task=task[:50],
            profile_items=len(context["profile"]),
            knowledge_items=len(context["relevant_knowledge"]),
            experience_items=len(context["past_experiences"]),
        )
        return context

    def build_prompt_context(self, task: str, agent_type: str | None = None) -> str:
        """Build a prompt string from memory context for injection."""
        ctx = self.get_context_for_task(task, agent_type)

        parts = []

        if ctx["profile"]:
            parts.append("## User Profile")
            for p in ctx["profile"]:
                parts.append(f"- {p}")

        if ctx["preferences"]:
            parts.append("\n## User Preferences")
            for p in ctx["preferences"]:
                parts.append(f"- {p}")

        if ctx["relevant_knowledge"]:
            parts.append("\n## Relevant Knowledge")
            for k in ctx["relevant_knowledge"]:
                parts.append(f"- {k['content'][:200]}")

        if ctx["past_experiences"]:
            parts.append("\n## Past Experiences")
            for e in ctx["past_experiences"]:
                parts.append(f"- {e['content'][:200]}")

        return "\n".join(parts)

    def record_task_memory(self, task: str, result: dict, success: bool) -> None:
        """Record task result as an experience memory."""
        summary = f"Task: {task[:100]}. Success: {success}."
        if result.get("agents"):
            summary += f" Agents: {', '.join(result.get('agents', []))}."

        self._mgr.save_memory(
            content=summary,
            memory_type=MemoryType.EXPERIENCE,
            importance=0.6 if success else 0.9,
            tags=["task-execution"] + (["success"] if success else ["failure"]),
            metadata={
                "task": task[:100],
                "success": success,
                "agents": result.get("agents", []),
                "duration_ms": result.get("duration_ms", 0),
            },
        )

        logger.info("Task memory recorded", task=task[:50], success=success)

    def record_user_input(self, content: str, memory_type: str = "knowledge", importance: float = 0.5) -> str:
        """Record a user input as memory."""
        record = self._mgr.save_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=["user-input"],
        )
        return record.id


# Global instance
_integration: MemoryIntegration | None = None


def get_memory_integration() -> MemoryIntegration:
    global _integration
    if _integration is None:
        _integration = MemoryIntegration()
    return _integration


def reset_memory_integration() -> None:
    global _integration
    _integration = None
