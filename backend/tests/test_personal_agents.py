"""Phase 5.5 tests - Personal Agent Team"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.personal_agents.roles import AgentRole, RoleConfig, PREDEFINED_ROLES, get_role_config, get_all_roles
from app.personal_agents.manager import PersonalAgentManager, TeamMember, DelegationRecord
from app.personal_agents.selector import PersonalAgentSelector
from app.main import app


class TestAgentRole:
    def test_all_roles_exist(self):
        roles = [r.value for r in AgentRole]
        assert "research" in roles
        assert "coding" in roles
        assert "writer" in roles
        assert "analyst" in roles

    def test_role_from_string(self):
        assert AgentRole("research") == AgentRole.RESEARCH
        assert AgentRole("coding") == AgentRole.CODING

    def test_invalid_role(self):
        with pytest.raises(ValueError):
            AgentRole("invalid")


class TestRoleConfig:
    def test_research_config(self):
        cfg = PREDEFINED_ROLES[AgentRole.RESEARCH]
        assert cfg.name == "Research Agent"
        assert "research" in cfg.capabilities

    def test_coding_config(self):
        cfg = PREDEFINED_ROLES[AgentRole.CODING]
        assert "coding" in cfg.capabilities
        assert "code_executor" in cfg.tools

    def test_writer_config(self):
        cfg = PREDEFINED_ROLES[AgentRole.WRITER]
        assert cfg.name == "Writer Agent"

    def test_analyst_config(self):
        cfg = PREDEFINED_ROLES[AgentRole.ANALYST]
        assert "analysis" in cfg.capabilities

    def test_get_role_config(self):
        cfg = get_role_config("research")
        assert cfg is not None
        assert cfg.name == "Research Agent"

    def test_get_role_config_none(self):
        assert get_role_config("nonexistent") is None

    def test_get_all_roles(self):
        roles = get_all_roles()
        assert len(roles) == 4


class TestTeamMember:
    def test_default_creation(self):
        m = TeamMember(role="research", name="Test")
        assert m.role == "research"
        assert m.active is True
        assert m.total_tasks == 0

    def test_success_rate_zero(self):
        m = TeamMember()
        assert m.success_rate == 0.0

    def test_success_rate_half(self):
        m = TeamMember(total_tasks=10, success_tasks=5)
        assert m.success_rate == 0.5

    def test_to_dict(self):
        m = TeamMember(role="coding", name="Coder", capabilities=["code"])
        d = m.to_dict()
        assert d["role"] == "coding"
        assert d["name"] == "Coder"
        assert "code" in d["capabilities"]


class TestPersonalAgentManager:
    def test_init_creates_team(self):
        mgr = PersonalAgentManager()
        members = mgr.list_members()
        assert len(members) == 4

    def test_list_members(self):
        mgr = PersonalAgentManager()
        members = mgr.list_members()
        roles = [m["role"] for m in members]
        assert "research" in roles
        assert "coding" in roles

    def test_get_member(self):
        mgr = PersonalAgentManager()
        members = mgr.list_members()
        mid = members[0]["id"]
        member = mgr.get_member(mid)
        assert member is not None

    def test_get_member_nonexistent(self):
        mgr = PersonalAgentManager()
        assert mgr.get_member("nonexistent") is None

    def test_get_member_by_role(self):
        mgr = PersonalAgentManager()
        member = mgr.get_member_by_role("research")
        assert member is not None
        assert member.role == "research"

    def test_update_member_stats(self):
        mgr = PersonalAgentManager()
        member = mgr.get_member_by_role("coding")
        mgr.update_member_stats(member.id, True, 500.0)
        assert member.total_tasks == 1
        assert member.success_tasks == 1
        assert member.avg_duration_ms == 500.0

    def test_record_delegation(self):
        mgr = PersonalAgentManager()
        member = mgr.get_member_by_role("research")
        mgr.record_delegation("task-1", member.id, "research", True, 300.0)
        delegations = mgr.get_delegations()
        assert len(delegations) == 1
        assert delegations[0]["task_id"] == "task-1"

    def test_team_stats(self):
        mgr = PersonalAgentManager()
        stats = mgr.get_team_stats()
        assert stats["total_members"] == 4
        assert stats["active_members"] == 4

    def test_update_stats_multiple(self):
        mgr = PersonalAgentManager()
        member = mgr.get_member_by_role("research")
        mgr.update_member_stats(member.id, True, 100.0)
        mgr.update_member_stats(member.id, False, 200.0)
        assert member.total_tasks == 2
        assert member.success_tasks == 1
        assert member.success_rate == 0.5


class TestPersonalAgentSelector:
    def test_select_by_role(self):
        mgr = PersonalAgentManager()
        selector = PersonalAgentSelector(mgr)
        member = selector.select(task_type="research")
        assert member is not None
        assert member.role == "research"

    def test_select_by_capabilities(self):
        mgr = PersonalAgentManager()
        selector = PersonalAgentSelector(mgr)
        member = selector.select(required_capabilities=["code"])
        assert member is not None

    def test_select_all_capable(self):
        mgr = PersonalAgentManager()
        selector = PersonalAgentSelector(mgr)
        members = selector.select_all_capable(["search"])
        assert len(members) >= 1

    def test_get_best_role_for_task_research(self):
        mgr = PersonalAgentManager()
        selector = PersonalAgentSelector(mgr)
        role = selector.get_best_role_for_task("research AI trends")
        assert role == "research"

    def test_get_best_role_for_task_coding(self):
        mgr = PersonalAgentManager()
        selector = PersonalAgentSelector(mgr)
        role = selector.get_best_role_for_task("fix the bug in code")
        assert role == "coding"

    def test_get_best_role_for_task_writing(self):
        mgr = PersonalAgentManager()
        selector = PersonalAgentSelector(mgr)
        role = selector.get_best_role_for_task("write a report")
        assert role == "writer"

    def test_get_best_role_for_task_analysis(self):
        mgr = PersonalAgentManager()
        selector = PersonalAgentSelector(mgr)
        role = selector.get_best_role_for_task("analyze the data")
        assert role == "analyst"

    def test_get_best_role_for_task_unknown(self):
        mgr = PersonalAgentManager()
        selector = PersonalAgentSelector(mgr)
        role = selector.get_best_role_for_task("hello world")
        assert role is None


class TestPersonalAgentsAPI:
    def _client(self):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def test_list_personal_agents(self):
        async with self._client() as c:
            resp = await c.get("/api/v1/agents/personal")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["members"]) == 4

    async def test_select_agent_by_type(self):
        async with self._client() as c:
            resp = await c.post("/api/v1/agents/select", json={"task_type": "coding"})
        data = resp.json()
        assert data["success"] is True
        assert data["member"]["role"] == "coding"

    async def test_select_by_task_description(self):
        async with self._client() as c:
            resp = await c.post("/api/v1/agents/select", json={"task_description": "write an article"})
        data = resp.json()
        assert data["success"] is True
        assert data["member"]["role"] == "writer"

    async def test_get_delegations(self):
        async with self._client() as c:
            resp = await c.get("/api/v1/agents/personal/delegations")
        data = resp.json()
        assert data["success"] is True
        assert "delegations" in data

    async def test_get_roles(self):
        async with self._client() as c:
            resp = await c.get("/api/v1/agents/personal/roles")
        data = resp.json()
        assert data["success"] is True
        assert len(data["roles"]) == 4
