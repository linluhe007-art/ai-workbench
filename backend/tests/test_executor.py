"""
PipelineExecutor 测试
覆盖：DAG 依赖顺序、单步骤、多步骤 pipeline、失败跳过、状态记录。
"""

import pytest

from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.orchestrator.pipeline_executor import PipelineExecutor, ExecutionResult
from app.orchestrator.executor import StepStatus
from app.agents.mock_agent import MockAgent


# === 辅助构建 ===

def _make_plan(steps: list[tuple]) -> TaskPlan:
    """
    快捷构建 TaskPlan
    steps: [(id, type, [depends_on]), ...]
    """
    task_steps = []
    for item in steps:
        sid, stype = item[0], item[1]
        deps = item[2] if len(item) > 2 else []
        task_steps.append(TaskStep(
            id=sid, type=stype, description=f"desc-{sid}", depends_on=deps,
        ))
    return TaskPlan(intent="test", steps=task_steps)


def _failing_agent(error_msg: str = "boom") -> MockAgent:
    """创建一个会抛异常的 Agent"""

    class _FailAgent(MockAgent):
        async def execute_step(self, step: TaskStep, context=None) -> dict:
            self._call_log.append({"step_id": step.id, "task_type": step.type.value, "description": step.description})
            raise RuntimeError(error_msg)

    return _FailAgent(agent_id="fail-agent")


# === 测试 ===

class TestSingleStep:

    @pytest.mark.asyncio
    async def test_single_step_success(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 1
        assert result.step_results["s1"].status == StepStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_single_step_with_custom_agent(self):
        agent = MockAgent("custom")
        agent.set_response("s1", {"answer": 42})

        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute(plan)

        assert result.step_results["s1"].output == {"answer": 42}


class TestDAGExecution:

    @pytest.mark.asyncio
    async def test_linear_pipeline(self):
        """research -> analysis -> writing 串行"""
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
        ])
        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 3
        # 验证顺序：research 应在 analysis 之前完成
        r_res = result.step_results["research"]
        a_res = result.step_results["analysis"]
        assert r_res.completed_at <= a_res.started_at

    @pytest.mark.asyncio
    async def test_parallel_branches(self):
        """analysis 之后 image 和 writing 并行"""
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
            ("image", TaskType.IMAGE, ["analysis"]),
        ])
        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 4

    @pytest.mark.asyncio
    async def test_full_content_pipeline(self):
        """完整 5 步 pipeline"""
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
            ("image", TaskType.IMAGE, ["analysis"]),
            ("seo", TaskType.SEO, ["writing"]),
        ])
        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 5
        assert result.duration_ms >= 0


class TestFailureHandling:

    @pytest.mark.asyncio
    async def test_step_failure_skips_dependents(self):
        """research 失败 → analysis 和 writing 被 skip"""
        fail_agent = _failing_agent("采集失败")

        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
        ])
        executor = PipelineExecutor(agent_map={"research": fail_agent})
        result = await executor.execute(plan)

        assert result.step_results["research"].status == StepStatus.FAILED
        assert result.step_results["analysis"].status == StepStatus.SKIPPED
        assert result.step_results["writing"].status == StepStatus.SKIPPED
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        """writing 失败但 research/analysis 成功 → partial"""
        fail_agent = _failing_agent("写作失败")

        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
        ])
        executor = PipelineExecutor(agent_map={"writing": fail_agent})
        result = await executor.execute(plan)

        assert result.step_results["research"].status == StepStatus.SUCCESS
        assert result.step_results["analysis"].status == StepStatus.SUCCESS
        assert result.step_results["writing"].status == StepStatus.FAILED
        assert result.status == "partial"
        assert result.success_count == 2

    @pytest.mark.asyncio
    async def test_parallel_branch_one_fails(self):
        """image 失败，writing 不受影响（不同分支）"""
        fail_agent = _failing_agent("图片生成失败")

        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
            ("image", TaskType.IMAGE, ["analysis"]),
        ])
        executor = PipelineExecutor(agent_map={"image": fail_agent})
        result = await executor.execute(plan)

        assert result.step_results["image"].status == StepStatus.FAILED
        assert result.step_results["writing"].status == StepStatus.SUCCESS
        assert result.status == "partial"


class TestAgentResolution:

    @pytest.mark.asyncio
    async def test_resolve_by_step_id(self):
        agent = MockAgent("special")
        agent.set_response("s1", {"special": True})

        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute(plan)

        assert result.step_results["s1"].output["special"] is True

    @pytest.mark.asyncio
    async def test_resolve_by_type(self):
        agent = MockAgent("type-agent")
        plan = _make_plan([("s1", TaskType.RESEARCH)])
        executor = PipelineExecutor(agent_map={"research": agent})
        result = await executor.execute(plan)

        assert result.step_results["s1"].agent_id == "type-agent"

    @pytest.mark.asyncio
    async def test_resolve_default(self):
        agent = MockAgent("default")
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"default": agent})
        result = await executor.execute(plan)

        assert result.step_results["s1"].agent_id == "default"

    @pytest.mark.asyncio
    async def test_auto_mock_when_no_agent(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.step_results["s1"].status == StepStatus.SUCCESS
        assert "auto-mock" in result.step_results["s1"].agent_id


class TestExecutionResult:

    @pytest.mark.asyncio
    async def test_to_dict(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        result = await PipelineExecutor().execute(plan)
        d = result.to_dict()

        assert "plan_intent" in d
        assert "steps" in d
        assert d["steps"]["s1"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_call_log(self):
        agent = MockAgent("log-agent")
        plan = _make_plan([("s1", TaskType.CHAT)])
        await PipelineExecutor(agent_map={"s1": agent}).execute(plan)

        assert len(agent.call_log) == 1
        assert agent.call_log[0]["step_id"] == "s1"