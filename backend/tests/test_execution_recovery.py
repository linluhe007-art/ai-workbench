"""
Phase 3.12.2 测试 — ExecutionRecoveryManager
覆盖：
- 成功无需恢复
- retryable 错误 retry
- agent 失败替换
- 不可恢复 abort
- RecoveryResult 结构
"""

import pytest
from datetime import datetime, timezone

from app.execution.recovery import ExecutionRecoveryManager, RecoveryResult
from app.execution.feedback import FeedbackResult
from app.orchestrator.pipeline_executor import ExecutionResult
from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.orchestrator.executor import StepResult, StepStatus
from app.agents.registry import AgentRegistry
from app.agents.mock_agent import MockAgent
from app.agents.selector import AgentSelector


# ─── helpers ───────────────────────────────────────────────


def _make_plan(steps: list[tuple[str, str, str]]) -> TaskPlan:
    """快捷构建 TaskPlan: [(id, type_str, agent_hint)]"""
    task_steps = []
    for sid, stype, hint in steps:
        task_steps.append(TaskStep(
            id=sid,
            type=TaskType(stype),
            description=f"desc-{sid}",
            agent_hint=hint,
            params={"capability": stype},
        ))
    return TaskPlan(intent="test", steps=task_steps)


def _make_exec_result(
    status: str,
    steps: list[tuple[str, str, str]],
) -> ExecutionResult:
    """快捷构建 ExecutionResult: [(id, status, error)]"""
    step_results = {}
    for sid, st, err in steps:
        step_results[sid] = StepResult(
            step_id=sid,
            status=StepStatus(st),
            agent_id=f"agent-{sid}",
            error=err,
        )
    return ExecutionResult(
        plan_intent="test",
        step_results=step_results,
        status=status,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


def _make_selector_with_agents(agents: list[tuple[str, list[str]]]) -> AgentSelector:
    """快捷创建 AgentSelector"""
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


class TestRecoverySuccess:

    @pytest.mark.asyncio
    async def test_success_returns_none(self):
        plan = _make_plan([("research", "research", "agent-a")])
        result = _make_exec_result("success", [("research", "success", "")])
        feedback = FeedbackResult(success=True, reason="ok")

        mgr = ExecutionRecoveryManager()
        recovery = await mgr.recover("task", plan, result, feedback)

        assert recovery.recovered is True
        assert recovery.action == "none"
        assert recovery.new_plan is None


# ═══════════════════════════════════════════════════════════
# Retryable 错误
# ═══════════════════════════════════════════════════════════


class TestRecoveryRetry:

    @pytest.mark.asyncio
    async def test_retryable_returns_retry(self):
        plan = _make_plan([("research", "research", "agent-a")])
        result = _make_exec_result("partial", [("research", "failed", "timeout")])
        feedback = FeedbackResult(
            success=False,
            failed_steps=["research"],
            retryable=True,
            reason="timeout",
        )

        mgr = ExecutionRecoveryManager()
        recovery = await mgr.recover("task", plan, result, feedback)

        assert recovery.recovered is True
        assert recovery.action == "retry"
        assert recovery.new_plan is None

    @pytest.mark.asyncio
    async def test_retry_preserves_plan(self):
        plan = _make_plan([
            ("research", "research", "agent-a"),
            ("writing", "writing", "agent-b"),
        ])
        result = _make_exec_result("partial", [
            ("research", "failed", "connection refused"),
            ("writing", "skipped", ""),
        ])
        feedback = FeedbackResult(
            success=False,
            failed_steps=["research"],
            skipped_steps=["writing"],
            retryable=True,
        )

        mgr = ExecutionRecoveryManager()
        recovery = await mgr.recover("task", plan, result, feedback)

        assert recovery.action == "retry"
        assert recovery.new_plan is None


# ═══════════════════════════════════════════════════════════
# Agent 替换
# ═══════════════════════════════════════════════════════════


class TestRecoveryAgentReplacement:

    @pytest.mark.asyncio
    async def test_replace_failed_agent(self):
        selector = _make_selector_with_agents([
            ("agent-a", ["research"]),
            ("agent-b", ["research"]),
        ])
        plan = _make_plan([("research", "research", "agent-a")])
        result = _make_exec_result("partial", [("research", "failed", "Invalid task")])
        feedback = FeedbackResult(
            success=False,
            failed_steps=["research"],
            retryable=False,
            reason="Invalid task",
        )

        mgr = ExecutionRecoveryManager(agent_selector=selector)
        recovery = await mgr.recover("task", plan, result, feedback)

        assert recovery.recovered is True
        assert recovery.action == "retry_agent"
        assert recovery.new_plan is not None
        assert recovery.replaced_agents["research"] == "agent-b"

    @pytest.mark.asyncio
    async def test_no_alternative_agent_aborts(self):
        selector = _make_selector_with_agents([
            ("agent-a", ["research"]),
        ])
        plan = _make_plan([("research", "research", "agent-a")])
        result = _make_exec_result("partial", [("research", "failed", "auth failed")])
        feedback = FeedbackResult(
            success=False,
            failed_steps=["research"],
            retryable=False,
            reason="auth failed",
        )

        mgr = ExecutionRecoveryManager(agent_selector=selector)
        recovery = await mgr.recover("task", plan, result, feedback)

        assert recovery.recovered is False
        assert recovery.action == "abort"

    @pytest.mark.asyncio
    async def test_no_selector_aborts(self):
        plan = _make_plan([("research", "research", "agent-a")])
        result = _make_exec_result("partial", [("research", "failed", "unsupported")])
        feedback = FeedbackResult(
            success=False,
            failed_steps=["research"],
            retryable=False,
            reason="unsupported",
        )

        mgr = ExecutionRecoveryManager(agent_selector=None)
        recovery = await mgr.recover("task", plan, result, feedback)

        assert recovery.recovered is False
        assert recovery.action == "abort"


# ═══════════════════════════════════════════════════════════
# RecoveryResult 结构
# ═══════════════════════════════════════════════════════════


class TestRecoveryResult:

    @pytest.mark.asyncio
    async def test_to_dict(self):
        plan = _make_plan([("research", "research", "agent-a")])
        result = _make_exec_result("success", [("research", "success", "")])
        feedback = FeedbackResult(success=True)

        mgr = ExecutionRecoveryManager()
        recovery = await mgr.recover("task", plan, result, feedback)
        d = recovery.to_dict()

        assert "recovered" in d
        assert "action" in d
        assert "reason" in d
        assert "has_new_plan" in d
        assert "replaced_agents" in d

    @pytest.mark.asyncio
    async def test_new_plan_preserves_intent(self):
        selector = _make_selector_with_agents([
            ("agent-a", ["research"]),
            ("agent-b", ["research"]),
        ])
        plan = _make_plan([("research", "research", "agent-a")])
        result = _make_exec_result("partial", [("research", "failed", "invalid")])
        feedback = FeedbackResult(
            success=False,
            failed_steps=["research"],
            retryable=False,
        )

        mgr = ExecutionRecoveryManager(agent_selector=selector)
        recovery = await mgr.recover("test task", plan, result, feedback)

        assert recovery.new_plan.intent == "test task"