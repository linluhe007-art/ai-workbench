"""
Phase 3.10.2 测试 — WorkflowGenerator
覆盖：
- 单能力任务
- 多能力任务
- DAG 依赖正确
- 无匹配 Agent
- 多个 Agent 选择
- 空任务异常
- AgentRegistry 集成
"""

import pytest

from app.planning.workflow import WorkflowGenerator
from app.orchestrator.planner import TaskType, TaskPlan
from app.agents.registry import AgentRegistry
from app.agents.capability import CapabilityRegistry
from app.agents.mock_agent import MockAgent
from app.agents.base import AgentType


# ═══════════════════════════════════════════════════════════
# 单能力任务
# ═══════════════════════════════════════════════════════════


class TestSingleCapability:

    def test_research_keyword(self):
        gen = WorkflowGenerator()
        plan = gen.generate("搜索资料")

        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.RESEARCH

    def test_analysis_keyword(self):
        gen = WorkflowGenerator()
        plan = gen.generate("分析市场趋势")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.ANALYSIS

    def test_writing_keyword(self):
        gen = WorkflowGenerator()
        plan = gen.generate("写一篇技术文章")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.WRITING

    def test_image_keyword(self):
        gen = WorkflowGenerator()
        plan = gen.generate("设计一张封面图片")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.IMAGE

    def test_seo_keyword(self):
        gen = WorkflowGenerator()
        plan = gen.generate("优化标题和标签")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.SEO

    def test_no_deps_on_single(self):
        gen = WorkflowGenerator()
        plan = gen.generate("搜索资料")

        assert plan.steps[0].depends_on == []


# ═══════════════════════════════════════════════════════════
# 多能力任务
# ═══════════════════════════════════════════════════════════


class TestMultiCapability:

    def test_research_and_writing(self):
        gen = WorkflowGenerator()
        plan = gen.generate("研究AI趋势并写报告")

        assert len(plan.steps) == 2
        types = [s.type for s in plan.steps]
        assert TaskType.RESEARCH in types
        assert TaskType.WRITING in types

    def test_full_pipeline(self):
        gen = WorkflowGenerator()
        plan = gen.generate("研究AI趋势，分析关键点，写一篇报告")

        assert len(plan.steps) == 3
        types = [s.type for s in plan.steps]
        assert types == [TaskType.RESEARCH, TaskType.ANALYSIS, TaskType.WRITING]

    def test_research_analysis_writing_order(self):
        gen = WorkflowGenerator()
        plan = gen.generate("研究并分析资料然后写报告")

        ids = [s.id for s in plan.steps]
        assert ids.index("research") < ids.index("analysis")
        assert ids.index("analysis") < ids.index("writing")


# ═══════════════════════════════════════════════════════════
# DAG 依赖
# ═══════════════════════════════════════════════════════════


class TestDAGDependencies:

    def test_first_step_no_deps(self):
        gen = WorkflowGenerator()
        plan = gen.generate("研究并写报告")

        assert plan.steps[0].depends_on == []

    def test_second_step_depends_on_first(self):
        gen = WorkflowGenerator()
        plan = gen.generate("研究并写报告")

        assert plan.steps[1].depends_on == [plan.steps[0].id]

    def test_chain_dependencies(self):
        gen = WorkflowGenerator()
        plan = gen.generate("研究AI趋势，分析关键点，写一篇报告，优化标题")

        steps = plan.steps
        assert steps[0].depends_on == []
        assert steps[1].depends_on == [steps[0].id]
        assert steps[2].depends_on == [steps[1].id]
        assert steps[3].depends_on == [steps[2].id]

    def test_step_ids_match_capabilities(self):
        gen = WorkflowGenerator()
        plan = gen.generate("研究并写报告")

        ids = {s.id for s in plan.steps}
        assert ids == {"research", "writing"}


# ═══════════════════════════════════════════════════════════
# Agent 选择
# ═══════════════════════════════════════════════════════════


class TestAgentSelection:

    def test_no_registry_agent_hint_empty(self):
        gen = WorkflowGenerator()
        plan = gen.generate("搜索资料")

        assert plan.steps[0].agent_hint == ""

    def test_with_registry_finds_agent(self):
        reg = AgentRegistry()
        reg.clear()
        agent = MockAgent("researcher", agent_type=AgentType.RESEARCH)
        agent.config.capabilities = ["research"]
        reg.register(agent)

        gen = WorkflowGenerator(agent_registry=reg)
        plan = gen.generate("搜索资料")

        assert plan.steps[0].agent_hint == "researcher"

    def test_no_matching_agent(self):
        reg = AgentRegistry()
        reg.clear()

        gen = WorkflowGenerator(agent_registry=reg)
        plan = gen.generate("搜索资料")

        assert plan.steps[0].agent_hint == ""

    def test_multiple_agents_picks_first(self):
        reg = AgentRegistry()
        reg.clear()
        a1 = MockAgent("agent-a")
        a1.config.capabilities = ["research"]
        a2 = MockAgent("agent-b")
        a2.config.capabilities = ["research"]
        reg.register(a1)
        reg.register(a2)

        gen = WorkflowGenerator(agent_registry=reg)
        plan = gen.generate("搜索资料")

        assert plan.steps[0].agent_hint in ("agent-a", "agent-b")


# ═══════════════════════════════════════════════════════════
# 边界情况
# ═══════════════════════════════════════════════════════════


class TestEdgeCases:

    def test_empty_task_raises(self):
        gen = WorkflowGenerator()
        with pytest.raises(ValueError, match="empty"):
            gen.generate("")

    def test_whitespace_only_raises(self):
        gen = WorkflowGenerator()
        with pytest.raises(ValueError, match="empty"):
            gen.generate("   ")

    def test_no_match_fallback_to_chat(self):
        gen = WorkflowGenerator()
        plan = gen.generate("你好世界")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.CHAT

    def test_plan_has_intent(self):
        gen = WorkflowGenerator()
        task = "研究AI趋势并写报告"
        plan = gen.generate(task)

        assert plan.intent == task

    def test_plan_has_context_query(self):
        gen = WorkflowGenerator()
        plan = gen.generate("研究AI趋势")

        assert plan.context_query

    def test_step_params_contain_input(self):
        gen = WorkflowGenerator()
        plan = gen.generate("搜索资料")

        assert plan.steps[0].params["user_input"] == "搜索资料"

    def test_step_description_contains_capability(self):
        gen = WorkflowGenerator()
        plan = gen.generate("写报告")

        assert "writing" in plan.steps[0].description