"""
ExecutionFeedbackManager — 执行反馈管理器。

分析 PipelineExecutor 的 ExecutionResult，
判断失败步骤是否可重试，生成反馈报告。
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.orchestrator.executor import StepStatus
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.orchestrator.pipeline_executor import ExecutionResult

logger = get_logger(__name__)

# 可重试的错误关键词
_RETRYABLE_KEYWORDS = [
    "timeout",
    "connection",
    "network",
    "rate limit",
    "temporary",
    "unavailable",
    "overloaded",
    "503",
    "429",
    "500",
]

# 不可重试的错误关键词
_NON_RETRYABLE_KEYWORDS = [
    "invalid task",
    "missing capability",
    "unsupported",
    "not found",
    "permission",
    "auth",
    "401",
    "403",
]


@dataclass
class FeedbackResult:
    """
    执行反馈结果。

    字段：
    - success: 整体是否成功
    - failed_steps: 失败步骤 ID 列表
    - skipped_steps: 跳过步骤 ID 列表
    - retryable: 是否建议重试
    - reason: 反馈摘要
    - step_details: 每个步骤的详情
    """
    success: bool
    failed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    retryable: bool = False
    reason: str = ""
    step_details: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "failed_steps": self.failed_steps,
            "skipped_steps": self.skipped_steps,
            "retryable": self.retryable,
            "reason": self.reason,
            "step_details": self.step_details,
        }


class ExecutionFeedbackManager:
    """
    执行反馈管理器。

    职责：
    - 分析 ExecutionResult
    - 识别失败步骤
    - 判断是否可重试
    - 生成反馈报告

    用法：
        manager = ExecutionFeedbackManager()
        feedback = manager.analyze(execution_result)
        if not feedback.success and feedback.retryable:
            # 重试逻辑
    """

    def analyze(self, result: "ExecutionResult") -> FeedbackResult:
        """
        分析执行结果。
        Args:
            result: PipelineExecutor 的执行结果
        Returns:
            FeedbackResult
        """
        if result.status == "success":
            return FeedbackResult(
                success=True,
                reason="All steps completed successfully",
                step_details=self._build_details(result),
            )

        failed_steps = []
        skipped_steps = []
        errors = []

        for step_id, step_result in result.step_results.items():
            if step_result.status == StepStatus.FAILED:
                failed_steps.append(step_id)
                if step_result.error:
                    errors.append(f"{step_id}: {step_result.error}")
            elif step_result.status == StepStatus.SKIPPED:
                skipped_steps.append(step_id)

        retryable = self._is_retryable(errors)
        reason = self._build_reason(failed_steps, skipped_steps, retryable, errors)

        logger.info(
            "Execution feedback",
            success=result.status == "success",
            failed=len(failed_steps),
            skipped=len(skipped_steps),
            retryable=retryable,
        )

        return FeedbackResult(
            success=False,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            retryable=retryable,
            reason=reason,
            step_details=self._build_details(result),
        )

    @staticmethod
    def _is_retryable(errors: list[str]) -> bool:
        """根据错误信息判断是否可重试"""
        if not errors:
            return False

        for error_msg in errors:
            error_lower = error_msg.lower()
            # 不可重试优先判断
            for keyword in _NON_RETRYABLE_KEYWORDS:
                if keyword in error_lower:
                    return False
            # 可重试关键词
            for keyword in _RETRYABLE_KEYWORDS:
                if keyword in error_lower:
                    return True

        # 默认：有错误则可重试（agent 异常通常可重试）
        return True

    @staticmethod
    def _build_reason(
        failed: list[str],
        skipped: list[str],
        retryable: bool,
        errors: list[str],
    ) -> str:
        """生成反馈摘要"""
        parts = []
        if failed:
            parts.append(f"Failed steps: {', '.join(failed)}")
        if skipped:
            parts.append(f"Skipped steps: {', '.join(skipped)}")
        if retryable:
            parts.append("Retry recommended")
        else:
            parts.append("Retry not recommended")
        if errors:
            parts.append(f"First error: {errors[0][:200]}")
        return "; ".join(parts)

    @staticmethod
    def _build_details(result: "ExecutionResult") -> list[dict]:
        """构建步骤详情列表"""
        details = []
        for step_id, sr in result.step_results.items():
            details.append({
                "step_id": step_id,
                "status": sr.status.value,
                "agent_id": sr.agent_id,
                "duration_ms": sr.duration_ms,
                "error": sr.error,
            })
        return details