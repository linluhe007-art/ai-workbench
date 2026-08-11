"""
Phase 3.11.2 测试 — AgentSelector
覆盖：
- 单 Agent 直接返回
- 多 Agent 评分排序
- 无 Agent 返回 None
- capability 匹配数量评分
- metadata.score 排序
- select_all
"""

import pytest

from app.agents.selector import AgentSelector
from app.agents.registry import AgentRegistry
from app.agents.mock_agent import MockAgent
from app.agents.base import AgentType


def _make_registry_with_agents(agents: list[tuple[str, list[str], dict]]) -> AgentRegistry:
    """快捷创建带 Agent 的 Registry"""
    reg = AgentRegistry()
    reg.clear()
    for agent_id, caps, extra in agents:
        agent = MockAgent(agent_id)
        agent.config.capabilities = caps
        if extra:
            agent.config.extra.update(extra)
        reg.register(agent)
    return reg


class TestAgentSelectorSingle:

    def test_single_agent(self):
        reg = _make_registry_with_agents([("a1", ["research"], {})])
        selector = AgentSelector(reg)
        assert selector.select("research") == "a1"

    def test_no_agent_returns_none(self):
        reg = AgentRegistry()
        reg.clear()
        selector = AgentSelector(reg)
        assert selector.select("research") is None

    def test_capability_not_found(self):
        reg = _make_registry_with_agents([("a1", ["research"], {})])
        selector = AgentSelector(reg)
        assert selector.select("writing") is None


class TestAgentSelectorMultiple:

    def test_two_agents_same_caps(self):
        reg = _make_registry_with_agents([
            ("a1", ["research"], {}),
            ("a2", ["research"], {}),
        ])
        selector = AgentSelector(reg)
        result = selector.select("research")
        assert result in ("a1", "a2")

    def test_more_caps_higher_score(self):
        """capability 更多的 Agent 应该被优先选择"""
        reg = _make_registry_with_agents([
            ("basic", ["research"], {}),
            ("advanced", ["research", "analysis", "writing"], {}),
        ])
        selector = AgentSelector(reg)
        assert selector.select("research") == "advanced"

    def test_meta_score_priority(self):
        """metadata.score 更高的 Agent 应该被优先选择"""
        reg = _make_registry_with_agents([
            ("a1", ["research"], {"score": 5}),
            ("a2", ["research"], {"score": 10}),
        ])
        selector = AgentSelector(reg)
        assert selector.select("research") == "a2"

    def test_score_overrides_order(self):
        """后注册但分数更高的 Agent 应该被选择"""
        reg = _make_registry_with_agents([
            ("first", ["research"], {"score": 1}),
            ("second", ["research"], {"score": 99}),
        ])
        selector = AgentSelector(reg)
        assert selector.select("research") == "second"


class TestAgentSelectorSelectAll:

    def test_select_all(self):
        reg = _make_registry_with_agents([
            ("a1", ["research"], {}),
            ("a2", ["research"], {}),
            ("a3", ["writing"], {}),
        ])
        selector = AgentSelector(reg)
        result = selector.select_all("research")
        assert set(result) == {"a1", "a2"}

    def test_select_all_empty(self):
        reg = AgentRegistry()
        reg.clear()
        selector = AgentSelector(reg)
        assert selector.select_all("research") == []