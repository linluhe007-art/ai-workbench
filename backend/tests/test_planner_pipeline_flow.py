"""
Phase 3.10.3 测试 — Planner → PipelineExecutor 集成流程
验证：
Planner.plan() → TaskPlan → PipelineExecutor.execute()
端到端可执行。
"""

import pytest

from app.planning.planner import Planner
from app.planning.workflow import WorkflowGenerator
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.orchestrator.executor import StepStatus
from app.agents.mock_agent import MockAgent
from app.agents.base import AgentType


class TestPlannerPipelineFlow:

    @pytest.mark.asyncio
    async def test_single_step_flow(self):
        """Planner → PipelineExecutor 单步执行"""
        planner = Planner.from_registry()
        plan = planner.plan("搜索资料")

        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 1

    @pytest.mark.asyncio
    async def test_multi_step_flow(self):
        """Planner → PipelineExecutor 多步串行"""
        planner = Planner.from_registry()
        plan = planner.plan("研究趋势并写报告")

        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 2
        # research 应在 writing 之前完成
        r = result.step_results["research"]
        w = result.step_results["writing"]
        assert r.completed_at <= w.started_at

    @pytest.mark.asyncio
    async def test_three_step_dag_flow(self):
        """Planner → PipelineExecutor 三步 DAG"""
        planner = Planner.from_registry()
        plan = planner.plan("研究趋势，分析数据，写报告")

        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 3
        assert result.step_results["analysis"].depends_on == ["research"]
        assert result.step_results["writing"].depends_on == ["analysis"]

    @pytest.mark.asyncio
    async def test_custom_agent_in_flow(self):
        """Planner 使用自定义 Agent，PipelineExecutor 正确调用"""
        research_agent = MockAgent("my-researcher", agent_type=AgentType.RESEARCH)
        research_agent.config.capabilities = ["research"]
        research_agent.set_response("research", {"custom": True})

        planner = Planner.from_registry()
        plan = planner.plan("搜索资料")

        executor = PipelineExecutor(agent_map={"research": research_agent})
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.step_results["research"].output["custom"] is True

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self):
        """完整 5 步 flow"""
        planner = Planner.from_registry()
        plan = planner.plan("研究AI趋势，分析数据，写报告，设计封面，优化标题")

        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 5

    @pytest.mark.asyncio
    async def test_flow_with_failure_isolation(self):
        """Pipeline 中某步失败不影响其他分支"""

        class FailAgent(MockAgent):
            async def execute_step(self, step, context=None):
                self._call_log.append({"step_id": step.id, "task_type": step.type.value, "description": step.description})
                if step.id == "research":
                    raise RuntimeError("采集失败")
                return self._build_output(step)

        fail_agent = FailAgent("fail-agent")

        planner = Planner.from_registry()
        plan = planner.plan("研究趋势并写报告")

        executor = PipelineExecutor(agent_map={"research": fail_agent})
        result = await executor.execute(plan)

        assert result.step_results["research"].status == StepStatus.FAILED
        assert result.step_results["writing"].status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_execution_result_has_plan_intent(self):
        """执行结果保留原始意图"""
        planner = Planner.from_registry()
        task = "研究并写报告"
        plan = planner.plan(task)

        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.plan_intent == task