"""
Phase 3.10.3 测试 — Planner 单元测试
覆盖：
- 初始化
- 简单任务
- 多步骤 DAG
- AgentRegistry 传递
- 空任务
- from_registry 工厂
"""

import pytest

from app.planning.planner import Planner
from app.planning.workflow import WorkflowGenerator
from app.orchestrator.planner import TaskPlan, TaskType
from app.agents.registry import AgentRegistry
from app.agents.mock_agent import MockAgent
from app.agents.base import AgentType


class TestPlannerInit:

    def test_init_with_generator(self):
        gen = WorkflowGenerator()
        planner = Planner(gen)
        assert planner._workflow is gen

    def test_from_registry(self):
        planner = Planner.from_registry()
        assert isinstance(planner._workflow, WorkflowGenerator)

    def test_from_registry_with_agent(self):
        reg = AgentRegistry()
        reg.clear()
        agent = MockAgent("researcher")
        agent.config.capabilities = ["research"]
        reg.register(agent)

        planner = Planner.from_registry(reg)
        plan = planner.plan("搜索资料")
        assert plan.steps[0].agent_hint == "researcher"


class TestPlannerSimpleTask:

    def test_single_research(self):
        planner = Planner.from_registry()
        plan = planner.plan("搜索资料")

        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.RESEARCH

    def test_single_writing(self):
        planner = Planner.from_registry()
        plan = planner.plan("写一篇文章")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.WRITING

    def test_single_analysis(self):
        planner = Planner.from_registry()
        plan = planner.plan("分析数据")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.ANALYSIS


class TestPlannerMultiStep:

    def test_two_steps(self):
        planner = Planner.from_registry()
        plan = planner.plan("研究AI趋势并写报告")

        assert len(plan.steps) == 2
        types = [s.type for s in plan.steps]
        assert TaskType.RESEARCH in types
        assert TaskType.WRITING in types

    def test_three_steps_chain(self):
        planner = Planner.from_registry()
        plan = planner.plan("研究趋势，分析数据，写报告")

        assert len(plan.steps) == 3
        assert plan.steps[0].type == TaskType.RESEARCH
        assert plan.steps[1].type == TaskType.ANALYSIS
        assert plan.steps[2].type == TaskType.WRITING
        assert plan.steps[1].depends_on == ["research"]
        assert plan.steps[2].depends_on == ["analysis"]

    def test_full_pipeline(self):
        planner = Planner.from_registry()
        plan = planner.plan("研究AI，分析趋势，写报告，做封面，优化标题")

        assert len(plan.steps) == 5


class TestPlannerEdgeCases:

    def test_empty_task_raises(self):
        planner = Planner.from_registry()
        with pytest.raises(ValueError, match="empty"):
            planner.plan("")

    def test_no_match_fallback(self):
        planner = Planner.from_registry()
        plan = planner.plan("你好")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.CHAT

    def test_plan_preserves_intent(self):
        planner = Planner.from_registry()
        task = "研究并写报告"
        plan = planner.plan(task)
        assert plan.intent == task