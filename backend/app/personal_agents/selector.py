"""Personal Agent Selector - Phase 5.5"""
from app.personal_agents.roles import AgentRole, PREDEFINED_ROLES
from app.personal_agents.manager import PersonalAgentManager, TeamMember
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PersonalAgentSelector:
    def __init__(self, manager: PersonalAgentManager, agent_registry=None):
        self._manager = manager
        self._registry = agent_registry

    def select(self, task_type: str = "", required_capabilities: list[str] | None = None, prefer_experienced: bool = True):
        candidates = self._manager.list_members()
        if not candidates:
            return None
        if required_capabilities:
            candidates = [m for m in candidates if any(c in m.get("capabilities", []) for c in required_capabilities)]
        if not candidates:
            return None
        if task_type:
            role_candidates = [m for m in candidates if m.get("role") == task_type]
            if role_candidates:
                candidates = role_candidates
        if prefer_experienced and len(candidates) > 1:
            candidates.sort(key=lambda m: (m.get("success_rate", 0), m.get("total_tasks", 0)), reverse=True)
        best = candidates[0]
        member = self._manager.get_member(best["id"])
        logger.info("Agent selected", role=best.get("role"), task_type=task_type)
        return member

    def select_all_capable(self, capabilities: list[str]) -> list[TeamMember]:
        result = []
        for m_data in self._manager.list_members():
            member = self._manager.get_member(m_data["id"])
            if member and any(c in member.capabilities for c in capabilities):
                result.append(member)
        return result

    def get_best_role_for_task(self, task_description: str) -> str | None:
        task_lower = task_description.lower()
        role_keywords = {
            "research": ["research", "search", "find", "explore", "investigate"],
            "coding": ["code", "program", "develop", "fix", "debug", "refactor"],
            "writer": ["write", "draft", "compose", "article", "report"],
            "analyst": ["analyze", "evaluate", "assess", "compare", "review"],
        }
        scores = {}
        for role, keywords in role_keywords.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > 0:
                scores[role] = score
        if not scores:
            return None
        return max(scores, key=scores.get)
