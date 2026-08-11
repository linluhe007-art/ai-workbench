"""
Phase 3.15 测试 — MemoryAwarePlanner
覆盖：
- 有历史经验时规划
- 无历史经验时规划
- MemoryContext 生成
- 推荐 Agent
- 警告生成
- 接口兼容
"""

import pytest
from app.planning.memory_planner import MemoryAwarePlanner
from app.planning.planner import Planner
from app.memory.experience import ExperienceMemory
from app.orchestrator.planner import TaskPlan, TaskType


class TestMemoryAwarePlannerBasic:

    @pytest.mark.asyncio
    async def test_plan_returns_tuple(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        planner = MemoryAwarePlanner(inner, mem)

        plan, ctx = await planner.plan("搜索资料")
        assert plan.intent == "搜索资料"
        assert ctx is not None

    @pytest.mark.asyncio
    async def test_plan_with_no_history(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        planner = MemoryAwarePlanner(inner, mem)

        plan, ctx = await planner.plan("研究AI趋势")
        assert len(plan.steps) >= 1
        assert ctx.has_history is False
        assert ctx.similar_tasks == []

    @pytest.mark.asyncio
    async def test_plan_with_history(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        mem.record_experience("研究AI趋势", ["agent-a"], True)
        mem.record_experience("研究AI趋势", ["agent-b"], False)

        planner = MemoryAwarePlanner(inner, mem)
        plan, ctx = await planner.plan("研究AI趋势")

        assert ctx.has_history is True
        assert len(ctx.similar_tasks) == 2

    @pytest.mark.asyncio
    async def test_context_has_success_rate(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        mem.record_experience("研究", ["a"], True)
        mem.record_experience("研究", ["a"], True)
        mem.record_experience("研究", ["a"], False)

        planner = MemoryAwarePlanner(inner, mem)
        _, ctx = await planner.plan("研究资料")

        assert ctx.historical_success_rate > 0


class TestMemoryAwarePlannerRecommendations:

    @pytest.mark.asyncio
    async def test_recommended_agents(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        mem.record_experience("研究AI", ["best-agent"], True)
        mem.record_experience("研究AI", ["best-agent"], True)
        mem.record_experience("研究AI", ["worst-agent"], False)

        planner = MemoryAwarePlanner(inner, mem)
        _, ctx = await planner.plan("研究AI")

        assert "best-agent" in ctx.recommended_agents

    @pytest.mark.asyncio
    async def test_no_recommendations_when_empty(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        planner = MemoryAwarePlanner(inner, mem)

        _, ctx = await planner.plan("全新任务")
        assert ctx.recommended_agents == []


class TestMemoryAwarePlannerWarnings:

    @pytest.mark.asyncio
    async def test_low_success_rate_warning(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        for _ in range(8):
            mem.record_experience("研究", ["a"], False)
        mem.record_experience("研究", ["a"], True)

        planner = MemoryAwarePlanner(inner, mem)
        _, ctx = await planner.plan("研究资料")

        assert len(ctx.warnings) > 0
        assert any("low" in w.lower() for w in ctx.warnings)

    @pytest.mark.asyncio
    async def test_no_warnings_on_good_history(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        mem.record_experience("研究", ["a"], True)
        mem.record_experience("研究", ["a"], True)

        planner = MemoryAwarePlanner(inner, mem)
        _, ctx = await planner.plan("研究资料")

        assert len(ctx.warnings) == 0


class TestMemoryAwarePlannerContext:

    @pytest.mark.asyncio
    async def test_context_to_dict(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        planner = MemoryAwarePlanner(inner, mem)

        _, ctx = await planner.plan("研究")
        d = ctx.to_dict()

        assert "similar_tasks_count" in d
        assert "recommended_agents" in d
        assert "historical_success_rate" in d
        assert "warnings" in d

    @pytest.mark.asyncio
    async def test_experience_memory_property(self):
        mem = ExperienceMemory()
        planner = MemoryAwarePlanner(Planner.from_registry(), mem)
        assert planner.experience_memory is mem

class TestMemoryAwarePlannerIntegration:

    @pytest.mark.asyncio
    async def test_plan_type_preserved(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        planner = MemoryAwarePlanner(inner, mem)

        plan, _ = await planner.plan("研究AI趋势并写报告")
        types = [s.type for s in plan.steps]
        assert TaskType.RESEARCH in types

    @pytest.mark.asyncio
    async def test_multiple_queries_accumulate(self):
        inner = Planner.from_registry()
        mem = ExperienceMemory()
        mem.record_experience("研究AI", ["a"], True)
        mem.record_experience("写报告", ["b"], True)

        planner = MemoryAwarePlanner(inner, mem)
        _, ctx1 = await planner.plan("研究AI")
        _, ctx2 = await planner.plan("写报告")

        assert ctx1.has_history is True
        assert ctx2.has_history is True

    @pytest.mark.asyncio
    async def test_default_retriever(self):
        inner = Planner.from_registry()
        planner = MemoryAwarePlanner(inner)
        plan, ctx = await planner.plan("搜索资料")
        assert plan.intent == "搜索资料"