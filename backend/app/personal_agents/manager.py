"""Personal Agent Manager - Phase 5.5"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.personal_agents.roles import AgentRole, RoleConfig, PREDEFINED_ROLES, get_role_config
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TeamMember:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = ""
    agent_id: str = ""
    name: str = ""
    capabilities: list[str] = field(default_factory=list)
    total_tasks: int = 0
    success_tasks: int = 0
    avg_duration_ms: float = 0.0
    active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return round(self.success_tasks / self.total_tasks, 4)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "role": self.role, "agent_id": self.agent_id,
            "name": self.name, "capabilities": self.capabilities,
            "total_tasks": self.total_tasks, "success_tasks": self.success_tasks,
            "success_rate": self.success_rate, "avg_duration_ms": self.avg_duration_ms,
            "active": self.active, "created_at": self.created_at,
        }


@dataclass
class DelegationRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    member_id: str = ""
    role: str = ""
    success: bool = False
    duration_ms: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {"id": self.id, "task_id": self.task_id, "member_id": self.member_id, "role": self.role, "success": self.success, "duration_ms": self.duration_ms, "created_at": self.created_at}


class PersonalAgentManager:
    def __init__(self, agent_registry=None):
        self._registry = agent_registry
        self._members: dict[str, TeamMember] = {}
        self._delegations: list[DelegationRecord] = []
        self._init_default_team()

    def _init_default_team(self):
        for role_config in PREDEFINED_ROLES.values():
            member = TeamMember(role=role_config.role.value, name=role_config.name, capabilities=role_config.capabilities)
            self._members[member.id] = member

    def list_members(self) -> list[dict]:
        return [m.to_dict() for m in self._members.values() if m.active]

    def get_member(self, member_id: str):
        return self._members.get(member_id)

    def get_member_by_role(self, role: str):
        for m in self._members.values():
            if m.role == role and m.active:
                return m
        return None

    def update_member_stats(self, member_id: str, success: bool, duration_ms: float):
        member = self._members.get(member_id)
        if member:
            member.total_tasks += 1
            if success:
                member.success_tasks += 1
            n = member.total_tasks
            member.avg_duration_ms = (member.avg_duration_ms * (n - 1) + duration_ms) / n

    def record_delegation(self, task_id: str, member_id: str, role: str, success: bool, duration_ms: float):
        record = DelegationRecord(task_id=task_id, member_id=member_id, role=role, success=success, duration_ms=duration_ms)
        self._delegations.append(record)
        self.update_member_stats(member_id, success, duration_ms)
        logger.info("Delegation recorded", task=task_id, role=role, success=success)

    def get_delegations(self, limit: int = 50) -> list[dict]:
        sorted_records = sorted(self._delegations, key=lambda r: r.created_at, reverse=True)
        return [r.to_dict() for r in sorted_records[:limit]]

    def get_team_stats(self) -> dict:
        total_tasks = sum(m.total_tasks for m in self._members.values())
        total_success = sum(m.success_tasks for m in self._members.values())
        return {"total_members": len(self._members), "active_members": sum(1 for m in self._members.values() if m.active), "total_tasks": total_tasks, "total_success": total_success, "overall_success_rate": round(total_success / total_tasks, 4) if total_tasks > 0 else 0.0}

    def clear(self):
        self._members.clear()
        self._delegations.clear()
