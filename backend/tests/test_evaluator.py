"""
Phase 3.17 测试 — Evaluator
"""

import pytest
from datetime import datetime, timezone
from app.evaluation.evaluator import (
    Evaluator, EvaluationResult,
    QUALITY_EXCELLENT, QUALITY_GOOD, QUALITY_ACCEPTABLE, QUALITY_POOR, QUALITY_FAILED,
)
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


class TestEvaluatorSuccess:

    @pytest.mark.asyncio
    async def test_all_success(self):
        result = _make_result("success", [("s1", "success", ""), ("s2", "success", "")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.success is True
        assert r.score >= 8.0
        assert r.quality in (QUALITY_EXCELLENT, QUALITY_GOOD)

    @pytest.mark.asyncio
    async def test_single_success(self):
        result = _make_result("success", [("s1", "success", "")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.success is True
        assert r.score >= 8.0


class TestEvaluatorPartial:

    @pytest.mark.asyncio
    async def test_partial(self):
        result = _make_result("partial", [
            ("s1", "success", ""), ("s2", "failed", "err"),
        ])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.success is False
        assert r.score < 8.0
        assert len(r.issues) > 0

    @pytest.mark.asyncio
    async def test_all_failed(self):
        result = _make_result("failed", [("s1", "failed", "err")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.success is False
        assert r.score <= 2.0
        assert r.quality == QUALITY_FAILED


class TestEvaluatorIssues:

    @pytest.mark.asyncio
    async def test_failed_step_recorded(self):
        result = _make_result("partial", [("s1", "failed", "timeout error")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert any("s1" in i for i in r.issues)

    @pytest.mark.asyncio
    async def test_skipped_step_recorded(self):
        result = _make_result("partial", [
            ("s1", "failed", "err"), ("s2", "skipped", ""),
        ])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert any("s2" in i and "skipped" in i for i in r.issues)


class TestEvaluatorSuggestions:

    @pytest.mark.asyncio
    async def test_failure_suggestions(self):
        result = _make_result("partial", [("s1", "failed", "err")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert len(r.suggestions) > 0

    @pytest.mark.asyncio
    async def test_success_suggestion(self):
        result = _make_result("success", [("s1", "success", "")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert any("success" in s.lower() for s in r.suggestions)


class TestEvaluatorThresholds:

    @pytest.mark.asyncio
    async def test_time_penalty(self):
        result = _make_result("success", [("s1", "success", "")])
        result.duration_ms = 60000
        ev = Evaluator(time_threshold_ms=10000)
        r = await ev.evaluate("task", result)
        assert any("took" in i.lower() for i in r.issues)

    @pytest.mark.asyncio
    async def test_custom_thresholds(self):
        result = _make_result("success", [("s1", "success", "")])
        ev = Evaluator(excellent_threshold=10.0, good_threshold=9.0)
        r = await ev.evaluate("task", result)
        assert r.quality == QUALITY_GOOD


class TestEvaluatorMetadata:

    @pytest.mark.asyncio
    async def test_metadata_fields(self):
        result = _make_result("success", [("s1", "success", "")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert "total_steps" in r.metadata
        assert "success_count" in r.metadata
        assert "completion_rate" in r.metadata

    @pytest.mark.asyncio
    async def test_empty_result(self):
        result = _make_result("failed", [])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.score == 0.0
        assert r.quality == QUALITY_FAILED

    @pytest.mark.asyncio
    async def test_to_dict(self):
        result = _make_result("success", [("s1", "success", "")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        d = r.to_dict()
        assert "score" in d
        assert "quality" in d
        assert "issues" in d
        assert "suggestions" in d

class TestEvaluatorQualityLevels:

    @pytest.mark.asyncio
    async def test_excellent_quality(self):
        result = _make_result("success", [("s1", "success", ""), ("s2", "success", "")])
        ev = Evaluator(excellent_threshold=8.0)
        r = await ev.evaluate("task", result)
        assert r.score >= 8.0

    @pytest.mark.asyncio
    async def test_acceptable_quality(self):
        result = _make_result("partial", [
            ("s1", "success", ""), ("s2", "failed", "err"),
        ])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.score >= 3.0

    @pytest.mark.asyncio
    async def test_poor_quality(self):
        result = _make_result("failed", [
            ("s1", "failed", "err"), ("s2", "failed", "err"),
        ])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.quality == QUALITY_FAILED


class TestEvaluatorCompletionRate:

    @pytest.mark.asyncio
    async def test_full_completion(self):
        result = _make_result("success", [("s1", "success", ""), ("s2", "success", "")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.metadata["completion_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_half_completion(self):
        result = _make_result("partial", [("s1", "success", ""), ("s2", "failed", "err")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.metadata["completion_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_zero_completion(self):
        result = _make_result("failed", [("s1", "failed", "err")])
        ev = Evaluator()
        r = await ev.evaluate("task", result)
        assert r.metadata["completion_rate"] == 0.0