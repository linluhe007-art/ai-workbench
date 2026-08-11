"""
Phase 3.12.1 测试 — ExecutionFeedbackManager
覆盖：
- 成功结果
- 单步骤失败
- 多步骤失败
- retryable 判断
- reason 生成
- skipped 步骤
- to_dict
"""

import pytest
from datetime import datetime, timezone

from app.execution.feedback import ExecutionFeedbackManager, FeedbackResult
from app.orchestrator.pipeline_executor import ExecutionResult
from app.orchestrator.executor import StepResult, StepStatus


# ─── helpers ───────────────────────────────────────────────


def _make_result(
    status: str = "success",
    steps: list[tuple[str, str, str]] | None = None,
) -> ExecutionResult:
    """
    快捷构建 ExecutionResult。
    steps: [(step_id, status_value, error), ...]
    """
    step_results = {}
    if steps:
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


# ═══════════════════════════════════════════════════════════
# 成功结果
# ═══════════════════════════════════════════════════════════


class TestFeedbackSuccess:

    def test_all_success(self):
        result = _make_result("success", [
            ("research", "success", ""),
            ("analysis", "success", ""),
            ("writing", "success", ""),
        ])
        mgr = ExecutionFeedbackManager()
        fb = mgr.analyze(result)

        assert fb.success is True
        assert fb.failed_steps == []
        assert fb.retryable is False
        assert "successfully" in fb.reason.lower()

    def test_empty_result_success(self):
        result = _make_result("success")
        mgr = ExecutionFeedbackManager()
        fb = mgr.analyze(result)

        assert fb.success is True


# ═══════════════════════════════════════════════════════════
# 失败步骤
# ═══════════════════════════════════════════════════════════


class TestFeedbackFailure:

    def test_single_failure(self):
        result = _make_result("partial", [
            ("research", "success", ""),
            ("writing", "failed", "agent timeout"),
        ])
        mgr = ExecutionFeedbackManager()
        fb = mgr.analyze(result)

        assert fb.success is False
        assert fb.failed_steps == ["writing"]
        assert "writing" in fb.reason

    def test_multiple_failures(self):
        result = _make_result("failed", [
            ("research", "failed", "network error"),
            ("analysis", "failed", "timeout"),
        ])
        mgr = ExecutionFeedbackManager()
        fb = mgr.analyze(result)

        assert fb.success is False
        assert set(fb.failed_steps) == {"research", "analysis"}
        assert len(fb.failed_steps) == 2

    def test_failure_with_skipped(self):
        result = _make_result("partial", [
            ("research", "failed", "error"),
            ("analysis", "skipped", ""),
            ("writing", "skipped", ""),
        ])
        mgr = ExecutionFeedbackManager()
        fb = mgr.analyze(result)

        assert fb.success is False
        assert fb.failed_steps == ["research"]
        assert set(fb.skipped_steps) == {"analysis", "writing"}


# ═══════════════════════════════════════════════════════════
# Retryable 判断
# ═══════════════════════════════════════════════════════════


class TestFeedbackRetryable:

    def test_timeout_is_retryable(self):
        result = _make_result("partial", [
            ("research", "failed", "Request timeout after 30s"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert fb.retryable is True

    def test_network_error_is_retryable(self):
        result = _make_result("partial", [
            ("research", "failed", "Connection refused"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert fb.retryable is True

    def test_rate_limit_is_retryable(self):
        result = _make_result("partial", [
            ("research", "failed", "Rate limit exceeded (429)"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert fb.retryable is True

    def test_agent_exception_is_retryable(self):
        result = _make_result("partial", [
            ("research", "failed", "RuntimeError: agent crashed"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert fb.retryable is True

    def test_invalid_task_not_retryable(self):
        result = _make_result("failed", [
            ("research", "failed", "Invalid task: unsupported format"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert fb.retryable is False

    def test_auth_error_not_retryable(self):
        result = _make_result("failed", [
            ("research", "failed", "Auth failed (401)"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert fb.retryable is False

    def test_permission_not_retryable(self):
        result = _make_result("failed", [
            ("research", "failed", "Permission denied"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert fb.retryable is False


# ═══════════════════════════════════════════════════════════
# Reason 生成
# ═══════════════════════════════════════════════════════════


class TestFeedbackReason:

    def test_success_reason(self):
        result = _make_result("success")
        fb = ExecutionFeedbackManager().analyze(result)
        assert "successfully" in fb.reason.lower()

    def test_failure_reason_contains_step_ids(self):
        result = _make_result("partial", [
            ("research", "failed", "error"),
            ("writing", "skipped", ""),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert "research" in fb.reason
        assert "writing" in fb.reason

    def test_retryable_hint_in_reason(self):
        result = _make_result("partial", [
            ("research", "failed", "timeout"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert "retry" in fb.reason.lower()

    def test_non_retryable_hint_in_reason(self):
        result = _make_result("failed", [
            ("research", "failed", "Invalid task"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        assert "not recommended" in fb.reason.lower()


# ═══════════════════════════════════════════════════════════
# step_details 和 to_dict
# ═══════════════════════════════════════════════════════════


class TestFeedbackDetails:

    def test_step_details(self):
        result = _make_result("partial", [
            ("research", "success", ""),
            ("writing", "failed", "boom"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)

        assert len(fb.step_details) == 2
        ids = {d["step_id"] for d in fb.step_details}
        assert ids == {"research", "writing"}

    def test_to_dict(self):
        result = _make_result("partial", [
            ("research", "failed", "error"),
        ])
        fb = ExecutionFeedbackManager().analyze(result)
        d = fb.to_dict()

        assert "success" in d
        assert "failed_steps" in d
        assert "retryable" in d
        assert "reason" in d
        assert "step_details" in d
        assert d["success"] is False