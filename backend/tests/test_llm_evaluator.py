"""
Phase 3.17 测试 — LLMEvaluator
"""

import json
import pytest
from datetime import datetime, timezone
from app.evaluation.llm_evaluator import LLMEvaluator
from app.evaluation.evaluator import Evaluator, EvaluationResult, QUALITY_GOOD, QUALITY_FAILED
from app.orchestrator.llm_provider import LLMProvider, LLMMessage, LLMResponse
from app.orchestrator.pipeline_executor import ExecutionResult
from app.orchestrator.executor import StepResult, StepStatus


def _make_result(status, steps):
    sr = {}
    for sid, st, err in steps:
        sr[sid] = StepResult(step_id=sid, status=StepStatus(st), agent_id=f"a-{sid}", error=err)
    return ExecutionResult(
        plan_intent="test", step_results=sr, status=status,
        started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc),
        duration_ms=100,
    )


class FakeEvalLLM(LLMProvider):
    def __init__(self, eval_json):
        self._data = eval_json

    async def chat(self, messages, **kwargs):
        return LLMResponse(content=json.dumps(self._data), model="fake-eval", tokens_used=50)


class FailingLLM(LLMProvider):
    async def chat(self, messages, **kwargs):
        raise RuntimeError("LLM down")


class TestLLMEvaluatorNormal:

    @pytest.mark.asyncio
    async def test_normal_evaluation(self):
        llm = FakeEvalLLM({
            "score": 8.5, "quality": "good",
            "issues": ["minor issue"], "suggestions": ["improve X"],
        })
        ev = LLMEvaluator(llm)
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)

        assert r.score == 8.5
        assert r.quality == "good"
        assert r.issues == ["minor issue"]
        assert r.suggestions == ["improve X"]

    @pytest.mark.asyncio
    async def test_score_clamped(self):
        llm = FakeEvalLLM({"score": 15, "quality": "good", "issues": [], "suggestions": []})
        ev = LLMEvaluator(llm)
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)
        assert r.score == 10.0

    @pytest.mark.asyncio
    async def test_invalid_quality_fallback(self):
        llm = FakeEvalLLM({"score": 5, "quality": "amazing", "issues": [], "suggestions": []})
        ev = LLMEvaluator(llm)
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)
        assert r.quality == "acceptable"


class TestLLMEvaluatorFallback:

    @pytest.mark.asyncio
    async def test_llm_failure_fallback(self):
        llm = FailingLLM()
        ev = LLMEvaluator(llm)
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)

        assert isinstance(r, EvaluationResult)
        assert r.score >= 0

    @pytest.mark.asyncio
    async def test_bad_json_fallback(self):
        class BadLLM(LLMProvider):
            async def chat(self, messages, **kwargs):
                return LLMResponse(content="not json", model="bad")

        ev = LLMEvaluator(BadLLM())
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)
        assert isinstance(r, EvaluationResult)

    @pytest.mark.asyncio
    async def test_markdown_json(self):
        data = {"score": 7.0, "quality": "good", "issues": [], "suggestions": []}
        json_str = json.dumps(data)

        class MDLLM(LLMProvider):
            async def chat(self, messages, **kwargs):
                return LLMResponse(content=f"```json\n{json_str}\n```", model="md")

        ev = LLMEvaluator(MDLLM())
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)
        assert r.score == 7.0

    @pytest.mark.asyncio
    async def test_custom_fallback(self):
        custom = Evaluator(time_threshold_ms=1000)
        ev = LLMEvaluator(FailingLLM(), fallback=custom)
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)
        assert isinstance(r, EvaluationResult)


class TestLLMEvaluatorMetadata:

    @pytest.mark.asyncio
    async def test_metadata_has_provider(self):
        llm = FakeEvalLLM({"score": 8, "quality": "good", "issues": [], "suggestions": []})
        ev = LLMEvaluator(llm)
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)
        assert r.metadata.get("provider") == "llm"

class TestLLMEvaluatorScoreRange:

    @pytest.mark.asyncio
    async def test_negative_score_clamped(self):
        llm = FakeEvalLLM({"score": -5, "quality": "failed", "issues": [], "suggestions": []})
        ev = LLMEvaluator(llm)
        result = _make_result("failed", [("s1", "failed", "")])
        r = await ev.evaluate("task", result)
        assert r.score == 0.0

    @pytest.mark.asyncio
    async def test_zero_score(self):
        llm = FakeEvalLLM({"score": 0, "quality": "failed", "issues": ["bad"], "suggestions": ["fix"]})
        ev = LLMEvaluator(llm)
        result = _make_result("failed", [("s1", "failed", "")])
        r = await ev.evaluate("task", result)
        assert r.score == 0.0
        assert r.quality == "failed"

    @pytest.mark.asyncio
    async def test_issues_and_suggestions(self):
        llm = FakeEvalLLM({
            "score": 6, "quality": "acceptable",
            "issues": ["step failed", "slow execution"],
            "suggestions": ["retry with different agent", "optimize pipeline"],
        })
        ev = LLMEvaluator(llm)
        result = _make_result("partial", [("s1", "failed", "err")])
        r = await ev.evaluate("task", result)
        assert len(r.issues) == 2
        assert len(r.suggestions) == 2

    @pytest.mark.asyncio
    async def test_success_result(self):
        llm = FakeEvalLLM({"score": 9.5, "quality": "excellent", "issues": [], "suggestions": ["well done"]})
        ev = LLMEvaluator(llm)
        result = _make_result("success", [("s1", "success", "")])
        r = await ev.evaluate("task", result)
        assert r.success is True
        assert r.score == 9.5