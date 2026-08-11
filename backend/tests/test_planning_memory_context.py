"""
Phase 3.15 测试 — PlanningMemoryContext
覆盖：
- 创建
- has_history
- to_dict
- warnings
- recommended_agents
"""

import pytest
from app.memory.context import PlanningMemoryContext


class TestPlanningMemoryContext:

    def test_default_empty(self):
        ctx = PlanningMemoryContext()
        assert ctx.similar_tasks == []
        assert ctx.recommended_agents == []
        assert ctx.historical_success_rate == 0.0
        assert ctx.warnings == []

    def test_has_history_true(self):
        ctx = PlanningMemoryContext(similar_tasks=[{"task": "a"}])
        assert ctx.has_history is True

    def test_has_history_false(self):
        ctx = PlanningMemoryContext()
        assert ctx.has_history is False

    def test_to_dict(self):
        ctx = PlanningMemoryContext(
            similar_tasks=[{"task": "a"}, {"task": "b"}],
            recommended_agents=["agent-1"],
            historical_success_rate=0.75,
            warnings=["warning1"],
        )
        d = ctx.to_dict()
        assert d["similar_tasks_count"] == 2
        assert d["recommended_agents"] == ["agent-1"]
        assert d["historical_success_rate"] == 0.75
        assert d["warnings"] == ["warning1"]

    def test_to_dict_rounds_rate(self):
        ctx = PlanningMemoryContext(historical_success_rate=0.666666)
        d = ctx.to_dict()
        assert d["historical_success_rate"] == 0.667

    def test_with_data(self):
        ctx = PlanningMemoryContext(
            similar_tasks=[
                {"task_pattern": "研究AI", "success": True},
                {"task_pattern": "研究AI", "success": False},
            ],
            recommended_agents=["best-agent"],
            historical_success_rate=0.5,
            warnings=["Low success rate"],
        )
        assert ctx.has_history is True
        assert len(ctx.similar_tasks) == 2
        assert "best-agent" in ctx.recommended_agents