"""
Evaluator — 规则型任务结果质量评估器。

根据 ExecutionResult 的各项指标评估执行质量，
输出 EvaluationResult 包含分数、问题和建议。
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.orchestrator.pipeline_executor import ExecutionResult

logger = get_logger(__name__)

# 质量等级
QUALITY_EXCELLENT = "excellent"
QUALITY_GOOD = "good"
QUALITY_ACCEPTABLE = "acceptable"
QUALITY_POOR = "poor"
QUALITY_FAILED = "failed"


@dataclass
class EvaluationResult:
    """
    评估结果。

    字段：
    - score: 质量分数 (0-10)
    - success: 是否成功
    - quality: 质量等级 (excellent/good/acceptable/poor/failed)
    - issues: 发现的问题列表
    - suggestions: 改进建议列表
    - metadata: 附加评估信息
    """
    score: float
    success: bool
    quality: str
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 2),
            "success": self.success,
            "quality": self.quality,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "metadata": self.metadata,
        }


class Evaluator:
    """
    规则型评估器。

    评分规则：
    - 基础分: 全部成功 = 8.0, 部分成功 = 5.0, 全部失败 = 0.0
    - 步骤完成率加分: +2.0 × completion_rate
    - 耗时惩罚: 超过阈值扣分
    - 失败步骤问题记录
    - 根据问题生成建议
    """

    def __init__(
        self,
        time_threshold_ms: int = 30000,
        excellent_threshold: float = 9.0,
        good_threshold: float = 7.0,
        acceptable_threshold: float = 5.0,
    ):
        self._time_threshold = time_threshold_ms
        self._excellent = excellent_threshold
        self._good = good_threshold
        self._acceptable = acceptable_threshold

    async def evaluate(
        self,
        task: str,
        result: "ExecutionResult",
    ) -> EvaluationResult:
        """
        评估执行结果质量。
        Args:
            task: 原始任务描述
            result: PipelineExecutor 的执行结果
        Returns:
            EvaluationResult
        """
        issues: list[str] = []
        suggestions: list[str] = []

        # 基础分
        total_steps = len(result.step_results)
        if total_steps == 0:
            return EvaluationResult(
                score=0.0, success=False, quality=QUALITY_FAILED,
                issues=["No steps in result"],
            )

        success_count = result.success_count
        failed_count = result.failed_count
        skipped_count = result.skipped_count
        completion_rate = success_count / total_steps if total_steps > 0 else 0.0

        # 基础分计算
        if result.status == "success":
            base_score = 8.0
        elif result.status == "partial":
            base_score = 5.0
        else:
            base_score = 0.0

        # 完成率加分
        score = base_score + 2.0 * completion_rate

        # 耗时惩罚
        if result.duration_ms > self._time_threshold:
            penalty = min(2.0, (result.duration_ms - self._time_threshold) / 10000)
            score -= penalty
            issues.append(f"Execution took {result.duration_ms}ms (threshold: {self._time_threshold}ms)")
            suggestions.append("Consider optimizing slow steps or increasing timeout")

        # 记录失败步骤
        for step_id, sr in result.step_results.items():
            if sr.status.value == "failed":
                issues.append(f"Step '{step_id}' failed: {sr.error[:200]}")
                suggestions.append(f"Retry step '{step_id}' or replace its agent")
            elif sr.status.value == "skipped":
                issues.append(f"Step '{step_id}' was skipped due to dependency failure")

        # 分数限制在 0-10
        score = max(0.0, min(10.0, score))

        # 质量等级
        quality = self._classify_quality(score)

        # 成功判断
        success = result.status == "success"

        if success and not issues:
            suggestions.append("Execution completed successfully")

        logger.info("Evaluation completed", score=round(score, 2), quality=quality, issues=len(issues))

        return EvaluationResult(
            score=score,
            success=success,
            quality=quality,
            issues=issues,
            suggestions=suggestions,
            metadata={
                "total_steps": total_steps,
                "success_count": success_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
                "duration_ms": result.duration_ms,
                "completion_rate": round(completion_rate, 3),
            },
        )

    def _classify_quality(self, score: float) -> str:
        if score >= self._excellent:
            return QUALITY_EXCELLENT
        elif score >= self._good:
            return QUALITY_GOOD
        elif score >= self._acceptable:
            return QUALITY_ACCEPTABLE
        elif score > 0:
            return QUALITY_POOR
        return QUALITY_FAILED