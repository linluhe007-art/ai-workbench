"""
Phase 3.15 测试 — AgentSelector with ExperienceMemory
覆盖：
- 无经验时保持原行为
- 有经验时成功率影响排序
- 失败经验惩罚
- 向后兼容
"""

import pytest
from app.agents.selector import AgentSelector
from app.agents.registry import AgentRegistry
from app.agents.mock_agent import MockAgent
from app.memory.experience import ExperienceMemory


def _make_reg(agents: list[tuple[str, list[str]]]) -> AgentRegistry:
    reg = AgentRegistry()
    reg.clear()
    for aid, caps in agents:
        a = MockAgent(aid)
        a.config.capabilities = caps
        reg.register(a)
    return reg


class TestSelectorWithoutExperience:

    def test_no_experience_keeps_original_behavior(self):
        reg = _make_reg([("a1", ["research"]), ("a2", ["research", "analysis"])])
        selector = AgentSelector(reg)
        assert selector.select("research") == "a2"

    def test_no_experience_single_agent(self):
        reg = _make_reg([("a1", ["research"])])
        selector = AgentSelector(reg)
        assert selector.select("research") == "a1"


class TestSelectorWithExperience:

    def test_experience_boosts_successful_agent(self):
        reg = _make_reg([("a1", ["research"]), ("a2", ["research"])])
        exp = ExperienceMemory()
        exp.record_experience("research", ["a1"], True)
        exp.record_experience("research", ["a1"], True)

        selector = AgentSelector(reg, experience=exp)
        assert selector.select("research") == "a1"

    def test_failure_penalty(self):
        reg = _make_reg([("a1", ["research"]), ("a2", ["research"])])
        exp = ExperienceMemory()
        exp.record_experience("research", ["a1"], False)
        exp.record_experience("research", ["a1"], False)

        selector = AgentSelector(reg, experience=exp)
        # a1 has bad history, a2 has no history (neutral)
        # a2 should be preferred
        result = selector.select("research")
        assert result == "a2"

    def test_mixed_history(self):
        reg = _make_reg([("a1", ["research"]), ("a2", ["research"])])
        exp = ExperienceMemory()
        exp.record_experience("research", ["a1"], True)
        exp.record_experience("research", ["a1"], True)
        exp.record_experience("research", ["a2"], False)

        selector = AgentSelector(reg, experience=exp)
        assert selector.select("research") == "a1"

    def test_context_task_pattern(self):
        reg = _make_reg([("a1", ["research"]), ("a2", ["research"])])
        exp = ExperienceMemory()
        exp.record_experience("研究AI", ["a1"], True)
        exp.record_experience("研究AI", ["a1"], True)

        selector = AgentSelector(reg, experience=exp)
        result = selector.select("research", context={"task_pattern": "研究AI"})
        assert result == "a1"


class TestSelectorBackwardCompat:

    def test_none_experience(self):
        reg = _make_reg([("a1", ["research"])])
        selector = AgentSelector(reg, experience=None)
        assert selector.select("research") == "a1"

    def test_empty_experience(self):
        reg = _make_reg([("a1", ["research"])])
        selector = AgentSelector(reg, experience=ExperienceMemory())
        assert selector.select("research") == "a1"

class TestSelectorExperienceEdgeCases:

    def test_all_agents_bad_history(self):
        reg = _make_reg([("a1", ["research"]), ("a2", ["research"])])
        exp = ExperienceMemory()
        exp.record_experience("research", ["a1"], False)
        exp.record_experience("research", ["a2"], False)

        selector = AgentSelector(reg, experience=exp)
        result = selector.select("research")
        assert result in ("a1", "a2")

    def test_experience_does_not_override_capability_count(self):
        reg = _make_reg([
            ("basic", ["research"]),
            ("advanced", ["research", "analysis", "writing"]),
        ])
        exp = ExperienceMemory()
        exp.record_experience("research", ["basic"], True)

        selector = AgentSelector(reg, experience=exp)
        # advanced has more caps (30 pts) vs basic with experience (20 pts)
        result = selector.select("research")
        assert result == "advanced"

    def test_select_all_still_works(self):
        reg = _make_reg([("a1", ["research"]), ("a2", ["research"])])
        exp = ExperienceMemory()
        selector = AgentSelector(reg, experience=exp)
        assert set(selector.select_all("research")) == {"a1", "a2"}