"""
Phase 3.13.1 测试 — execute_with_recovery 集成流程
覆盖：
- 成功无需恢复
- timeout 自动 retry
- agent 失败自动 retry
- retry 次数限制
- agent 替换 retry_agent
- 上下文保持
"""

import asyncio
import pytest
from datetime import datetime, timezone

from app.orchestrator.pipeline_executor import PipelineExecutor, ExecutionResult
from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.orchestrator.executor import StepResult, StepStatus
from app.agents.mock_agent import MockAgent
from app.agents.base import AgentType
from app.agents.registry import AgentRegistry
from app.agents.selector import AgentSelector


# ─── helpers ───────────────────────────────────────────────


def _make_plan(steps: list[tuple]) -> TaskPlan:
    """[(id, type, [depends_on], [agent_hint])]"""
    task_steps = []
    for item in steps:
        sid = item[0]
        stype = item[1]
        deps = item[2] if len(item) > 2 else []
        hint = item[3] if len(item) > 3 else ""
        task_steps.append(TaskStep(
            id=sid, type=stype, description=f"desc-{sid}",
            depends_on=deps, agent_hint=hint,
            params={"capability": stype.value},
        ))
    return TaskPlan(intent="test task", steps=task_steps)


def _fail_then_succeed(agent_id: str, fail_count: int):
    """创建一个前 N 次失败、之后成功的 Agent"""
    class _FailThenSucceed(MockAgent):
        def __init__(self):
            super().__init__(agent_id)
            self._attempt = 0

        async def execute_step(self, step, context=None):
            self._attempt += 1
            self._call_log.append({
                "step_id": step.id,
                "task_type": step.type.value,
                "description": step.description,
            })
            if self._attempt <= fail_count:
                raise RuntimeError("timeout: request timed out")
            return self._build_output(step)

    return _FailThenSucceed()


def _always_fail(agent_id: str, error: str = "boom"):
    """创建一个始终失败的 Agent"""

    class _AlwaysFail(MockAgent):
        async def execute_step(self, step, context=None):
            self._call_log.append({
                "step_id": step.id,
                "task_type": step.type.value,
                "description": step.description,
            })
            raise RuntimeError(error)

    return _AlwaysFail(agent_id)


def _make_selector(agents: list[tuple[str, list[str]]]) -> AgentSelector:
    reg = AgentRegistry()
    reg.clear()
    for aid, caps in agents:
        agent = MockAgent(aid)
        agent.config.capabilities = caps
        reg.register(agent)
    return AgentSelector(reg)


# ═══════════════════════════════════════════════════════════
# 成功无需恢复
# ═══════════════════════════════════════════════════════════


class TestRecoveryFlowSuccess:

    @pytest.mark.asyncio
    async def test_success_no_recovery(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor()
        result = await executor.execute_with_recovery(plan)

        assert result.status == "success"
        assert result.success_count == 1

    @pytest.mark.asyncio
    async def test_multi_step_success(self):
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
        ])
        executor = PipelineExecutor()
        result = await executor.execute_with_recovery(plan)

        assert result.status == "success"
        assert result.success_count == 2


# ═══════════════════════════════════════════════════════════
# Timeout 自动 retry
# ═══════════════════════════════════════════════════════════


class TestRecoveryFlowTimeout:

    @pytest.mark.asyncio
    async def test_timeout_retry_succeeds(self):
        """第一次 timeout，第二次成功"""
        agent = _fail_then_succeed("a1", fail_count=1)
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute_with_recovery(plan, max_retries=2)

        assert result.status == "success"
        assert agent._attempt == 2

    @pytest.mark.asyncio
    async def test_timeout_all_retries_fail(self):
        """每次都 timeout，超过 max_retries"""
        agent = _always_fail("a1", "timeout after 30s")
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute_with_recovery(plan, max_retries=2)

        assert result.status == "failed"
        assert agent._attempt == 3  # 1 initial + 2 retries


# ═══════════════════════════════════════════════════════════
# Agent 失败 retry
# ═══════════════════════════════════════════════════════════


class TestRecoveryFlowAgentFail:

    @pytest.mark.asyncio
    async def test_agent_exception_retryable(self):
        """RuntimeError 被视为 retryable"""
        agent = _fail_then_succeed("a1", fail_count=1)
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute_with_recovery(plan, max_retries=2)

        assert result.status == "success"


# ═══════════════════════════════════════════════════════════
# Retry 次数限制
# ═══════════════════════════════════════════════════════════


class TestRecoveryFlowRetryLimit:

    @pytest.mark.asyncio
    async def test_max_retries_zero(self):
        """max_retries=0 不重试"""
        agent = _always_fail("a1", "timeout")
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute_with_recovery(plan, max_retries=0)

        assert result.status == "failed"
        assert agent._attempt == 1

    @pytest.mark.asyncio
    async def test_max_retries_one(self):
        """max_retries=1 重试一次"""
        agent = _fail_then_succeed("a1", fail_count=2)
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute_with_recovery(plan, max_retries=1)

        # 2 failures but max_retries=1, so only 1 retry (total 2 attempts)
        assert result.status == "failed"
        assert agent._attempt == 2


# ═══════════════════════════════════════════════════════════
# Agent 替换 retry_agent
# ═══════════════════════════════════════════════════════════


class TestRecoveryFlowAgentReplace:

    @pytest.mark.asyncio
    async def test_non_retryable_replaces_agent(self):
        """不可重试错误 + 有替代 Agent → retry_agent"""
        bad_agent = _always_fail("bad", "Invalid task: unsupported")
        good_agent = MockAgent("good")
        good_agent.config.capabilities = ["custom"]

        selector = _make_selector([
            ("bad", ["custom"]),
            ("good", ["custom"]),
        ])

        plan = _make_plan([("s1", TaskType.CUSTOM, [], "bad")])
        executor = PipelineExecutor(agent_map={"bad": bad_agent, "good": good_agent})
        result = await executor.execute_with_recovery(
            plan, max_retries=2, agent_selector=selector,
        )

        # Should succeed with the good agent
        assert result.status == "success"


# ═══════════════════════════════════════════════════════════
# 上下文保持
# ═══════════════════════════════════════════════════════════


class TestRecoveryFlowContext:

    @pytest.mark.asyncio
    async def test_execution_result_preserves_intent(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor()
        result = await executor.execute_with_recovery(plan)

        assert result.plan_intent == "test task"

    @pytest.mark.asyncio
    async def test_duration_is_positive(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor()
        result = await executor.execute_with_recovery(plan)

        assert result.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_step_results_preserved(self):
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
        ])
        executor = PipelineExecutor()
        result = await executor.execute_with_recovery(plan)

        assert "research" in result.step_results
        assert "analysis" in result.step_results
        assert result.step_results["research"].status == StepStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_to_dict_after_recovery(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor()
        result = await executor.execute_with_recovery(plan)
        d = result.to_dict()

        assert "plan_intent" in d
        assert "steps" in d
        assert "status" in d