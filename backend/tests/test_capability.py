"""
Phase 3.10.1 测试 — Agent Capability System
覆盖：
- CapabilityRegistry 注册/注销
- 按能力查询 Agent
- 多 Agent 同能力
- AgentRegistry 集成
- BaseAgent capabilities
"""

import pytest

from app.agents.capability import CapabilityRegistry
from app.agents.registry import AgentRegistry
from app.agents.mock_agent import MockAgent
from app.agents.base import AgentConfig, AgentType


# ═══════════════════════════════════════════════════════════
# CapabilityRegistry 测试
# ═══════════════════════════════════════════════════════════


class TestCapabilityRegistryRegister:

    def test_register(self):
        reg = CapabilityRegistry()
        reg.register("agent-1", ["research", "analysis"])
        assert set(reg.get_capabilities("agent-1")) == {"research", "analysis"}

    def test_register_appends(self):
        reg = CapabilityRegistry()
        reg.register("agent-1", ["research"])
        reg.register("agent-1", ["analysis"])
        assert set(reg.get_capabilities("agent-1")) == {"research", "analysis"}

    def test_register_empty(self):
        reg = CapabilityRegistry()
        reg.register("agent-1", [])
        assert reg.get_capabilities("agent-1") == []


class TestCapabilityRegistryUnregister:

    def test_unregister(self):
        reg = CapabilityRegistry()
        reg.register("agent-1", ["research", "analysis"])
        reg.unregister("agent-1")
        assert reg.get_capabilities("agent-1") == []

    def test_unregister_removes_from_index(self):
        reg = CapabilityRegistry()
        reg.register("agent-1", ["research"])
        reg.unregister("agent-1")
        assert reg.get_agents_by_capability("research") == []

    def test_unregister_nonexistent(self):
        reg = CapabilityRegistry()
        reg.unregister("ghost")

    def test_unregister_preserves_others(self):
        reg = CapabilityRegistry()
        reg.register("a1", ["research"])
        reg.register("a2", ["research"])
        reg.unregister("a1")
        assert reg.get_agents_by_capability("research") == ["a2"]


class TestCapabilityRegistryQuery:

    def test_get_agents_by_capability(self):
        reg = CapabilityRegistry()
        reg.register("a1", ["research"])
        reg.register("a2", ["research", "writing"])
        reg.register("a3", ["writing"])

        researchers = reg.get_agents_by_capability("research")
        assert set(researchers) == {"a1", "a2"}

    def test_get_agents_by_capability_none(self):
        reg = CapabilityRegistry()
        assert reg.get_agents_by_capability("nonexistent") == []

    def test_get_capabilities(self):
        reg = CapabilityRegistry()
        reg.register("a1", ["research", "analysis", "writing"])
        assert set(reg.get_capabilities("a1")) == {"research", "analysis", "writing"}

    def test_get_capabilities_unknown(self):
        reg = CapabilityRegistry()
        assert reg.get_capabilities("ghost") == []

    def test_list_capabilities(self):
        reg = CapabilityRegistry()
        reg.register("a1", ["research"])
        reg.register("a2", ["research", "writing"])

        index = reg.list_capabilities()
        assert set(index["research"]) == {"a1", "a2"}
        assert index["writing"] == ["a2"]

    def test_list_capabilities_empty(self):
        reg = CapabilityRegistry()
        assert reg.list_capabilities() == {}


class TestCapabilityRegistryHelpers:

    def test_has_capability(self):
        reg = CapabilityRegistry()
        reg.register("a1", ["research"])
        assert reg.has_capability("a1", "research") is True
        assert reg.has_capability("a1", "writing") is False

    def test_has_capability_unknown_agent(self):
        reg = CapabilityRegistry()
        assert reg.has_capability("ghost", "research") is False

    def test_len(self):
        reg = CapabilityRegistry()
        reg.register("a1", ["research"])
        reg.register("a2", ["writing"])
        assert len(reg) == 2

    def test_clear(self):
        reg = CapabilityRegistry()
        reg.register("a1", ["research"])
        reg.register("a2", ["writing"])
        reg.clear()
        assert len(reg) == 0
        assert reg.list_capabilities() == {}


# ═══════════════════════════════════════════════════════════
# AgentRegistry 集成测试
# ═══════════════════════════════════════════════════════════


class TestAgentRegistryCapabilityIntegration:

    def test_register_auto_syncs_capabilities(self):
        reg = AgentRegistry()
        reg.clear()

        agent = MockAgent("researcher", agent_type=AgentType.RESEARCH)
        agent.config.capabilities = ["research", "search"]
        reg.register(agent)

        caps = reg.capabilities.get_capabilities("researcher")
        assert set(caps) == {"research", "search"}

    def test_unregister_auto_removes_capabilities(self):
        reg = AgentRegistry()
        reg.clear()

        agent = MockAgent("researcher")
        agent.config.capabilities = ["research"]
        reg.register(agent)
        reg.unregister("researcher")

        assert reg.capabilities.get_agents_by_capability("research") == []

    def test_get_agents_by_capability(self):
        reg = AgentRegistry()
        reg.clear()

        a1 = MockAgent("a1")
        a1.config.capabilities = ["research"]
        a2 = MockAgent("a2")
        a2.config.capabilities = ["research", "writing"]
        reg.register(a1)
        reg.register(a2)

        researchers = reg.get_agents_by_capability("research")
        assert set(researchers) == {"a1", "a2"}

    def test_capabilities_property(self):
        reg = AgentRegistry()
        assert isinstance(reg.capabilities, CapabilityRegistry)


# ═══════════════════════════════════════════════════════════
# BaseAgent capabilities 测试
# ═══════════════════════════════════════════════════════════


class TestBaseAgentCapabilities:

    def test_default_capabilities_empty(self):
        agent = MockAgent("a1")
        assert agent.get_capabilities() == ["mock", "test"]

    def test_config_capabilities(self):
        config = AgentConfig(
            id="custom", name="Custom", type=AgentType.CUSTOM,
            capabilities=["research", "analysis"],
        )
        agent = MockAgent("custom")
        agent.config = config
        assert set(agent.get_capabilities()) == {"research", "analysis"}

    def test_to_dict_includes_capabilities(self):
        agent = MockAgent("a1")
        agent.config.capabilities = ["research"]
        d = agent.to_dict()
        assert "capabilities" in d
        assert "research" in d["capabilities"]