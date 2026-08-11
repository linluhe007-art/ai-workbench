"""
LLMEvaluator — LLM 驱动的质量评估器。

使用 LLM 对执行结果进行更细致的质量评估。
LLM 返回 JSON 格式的评估结果。
失败时 fallback 到规则型 Evaluator。
"""

import json
from typing import TYPE_CHECKING

from app.evaluation.evaluator import (
    Evaluator,
    EvaluationResult,
    QUALITY_EXCELLENT,
    QUALITY_GOOD,
    QUALITY_ACCEPTABLE,
    QUALITY_POOR,
    QUALITY_FAILED,
)
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.orchestrator.llm_provider import LLMProvider
    from app.orchestrator.pipeline_executor import ExecutionResult

logger = get_logger(__name__)

EVAL_PROMPT = """你是一个任务执行质量评估器。请评估以下任务执行结果。

任务描述：{task}

执行状态：{status}
成功步骤：{success_count}
失败步骤：{failed_count}
耗时：{duration_ms}ms

失败详情：
{failure_details}

请返回 JSON 格式（不要包含其他内容）：
{{
  "score": 0-10的分数,
  "quality": "excellent/good/acceptable/poor/failed",
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}}"""


class LLMEvaluator:
    """
    LLM 驱动的质量评估器。

    流程：
    1. 构建评估 Prompt
    2. 调用 LLM 获取 JSON 评估
    3. 解析并返回 EvaluationResult
    4. 失败时 fallback 到规则型 Evaluator
    """

    def __init__(self, llm_provider: "LLMProvider", fallback: Evaluator | None = None):
        self._llm = llm_provider
        self._fallback = fallback or Evaluator()

    async def evaluate(
        self,
        task: str,
        result: "ExecutionResult",
    ) -> EvaluationResult:
        """
        使用 LLM 评估执行结果。
        Args:
            task: 原始任务描述
            result: 执行结果
        Returns:
            EvaluationResult
        """
        try:
            return await self._evaluate_with_llm(task, result)
        except Exception as e:  # noqa: BLE001 fallback on LLM failure
            logger.warning("LLM evaluation failed, falling back to rule-based", error=str(e))
            return await self._fallback.evaluate(task, result)

    async def _evaluate_with_llm(
        self,
        task: str,
        result: "ExecutionResult",
    ) -> EvaluationResult:
        from app.orchestrator.llm_provider import LLMMessage, LLMRole

        # 构建失败详情
        failure_lines = []
        for sid, sr in result.step_results.items():
            if sr.status.value in ("failed", "skipped"):
                failure_lines.append(f"  - {sid}: {sr.status.value} - {sr.error[:100]}")
        failure_details = "\n".join(failure_lines) if failure_lines else "  无"

        prompt = EVAL_PROMPT.format(
            task=task[:200],
            status=result.status,
            success_count=result.success_count,
            failed_count=result.failed_count,
            duration_ms=result.duration_ms,
            failure_details=failure_details,
        )

        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content="你是质量评估器，只输出JSON。"),
            LLMMessage(role=LLMRole.USER, content=prompt),
        ]

        response = await self._llm.chat(messages=messages, temperature=0.3)
        data = self._parse_response(response.content)

        # 质量等级标准化
        quality = data.get("quality", QUALITY_ACCEPTABLE)
        valid_qualities = {QUALITY_EXCELLENT, QUALITY_GOOD, QUALITY_ACCEPTABLE, QUALITY_POOR, QUALITY_FAILED}
        if quality not in valid_qualities:
            quality = QUALITY_ACCEPTABLE

        score = float(data.get("score", 5.0))
        score = max(0.0, min(10.0, score))

        return EvaluationResult(
            score=score,
            success=result.status == "success",
            quality=quality,
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            metadata={"provider": "llm", "model": response.model},
        )

    @staticmethod
    def _parse_response(content: str) -> dict:
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)
        return json.loads(text)