"""
Phase 3.17 测试 — TaskLoopManager with Evaluation
"""

import pytest
from app.execution.task_loop import TaskLoopManager
from app.execution.history import ExecutionHistory
from app.evaluation.evaluator import Evaluator, EvaluationResult, QUALITY_POOR
from app.planning.planner import Planner
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.agents.mock_agent import MockAgent


class TestTaskLoopWithEvaluator:

    @pytest.mark.asyncio
    async def test_success_with_evaluation(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        evaluator = Evaluator()
        loop = TaskLoopManager(planner, executor, evaluator=evaluator)

        result = await loop.run("搜索资料", max_iterations=2)

        assert result.success is True
        assert result.evaluation is not None
        assert result.evaluation.score >= 0

    @pytest.mark.asyncio
    async def test_no_evaluator(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor, evaluator=None)

        result = await loop.run("搜索资料")
        assert result.success is True
        assert result.evaluation is None

    @pytest.mark.asyncio
    async def test_quality_threshold_triggers_replan(self):
        """低质量评估应触发重新规划"""

        class LowScoreEvaluator(Evaluator):
            async def evaluate(self, task, result):
                return EvaluationResult(
                    score=2.0, success=True, quality=QUALITY_POOR,
                    issues=["low quality"], suggestions=["improve"],
                )

        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(
            planner, executor,
            evaluator=LowScoreEvaluator(),
            quality_threshold=8.0,
        )

        result = await loop.run("搜索资料", max_iterations=2)

        # 应该进行了2次迭代（第一次质量不达标，重试）
        assert result.iterations == 2
        assert result.success is True

    @pytest.mark.asyncio
    async def test_high_quality_stops_early(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(
            planner, executor,
            evaluator=Evaluator(),
            quality_threshold=5.0,
        )

        result = await loop.run("搜索资料", max_iterations=3)
        assert result.success is True
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_evaluation_in_loop_result(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor, evaluator=Evaluator())

        result = await loop.run("搜索资料")
        assert result.evaluation is not None
        assert result.evaluation.to_dict()["score"] >= 0


class TestTaskLoopEvaluationIntegration:

    @pytest.mark.asyncio
    async def test_evaluation_with_experience(self):
        from app.memory.experience import ExperienceMemory
        exp = ExperienceMemory()
        planner = Planner.from_registry()
        executor = PipelineExecutor(experience=exp)
        loop = TaskLoopManager(planner, executor, evaluator=Evaluator())

        result = await loop.run("搜索资料")
        assert result.success is True
        assert exp.total_records >= 1

    @pytest.mark.asyncio
    async def test_evaluation_with_history(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        history = ExecutionHistory()
        loop = TaskLoopManager(planner, executor, evaluator=Evaluator(), history=history)

        result = await loop.run("搜索资料")
        assert history.total_entries >= 1

    @pytest.mark.asyncio
    async def test_loop_result_to_dict_has_evaluation(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor, evaluator=Evaluator())

        result = await loop.run("搜索资料")
        d = result.to_dict()
        assert "success" in d
        assert "iterations" in d

    @pytest.mark.asyncio
    async def test_multi_step_evaluation(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor, evaluator=Evaluator())

        result = await loop.run("研究趋势并写报告", max_iterations=2)
        assert result.evaluation is not None
        assert result.evaluation.metadata.get("total_steps", 0) >= 2

class TestTaskLoopEvaluationEdgeCases:

    @pytest.mark.asyncio
    async def test_threshold_zero_accepts_all(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(
            planner, executor,
            evaluator=Evaluator(),
            quality_threshold=0.0,
        )
        result = await loop.run("搜索资料", max_iterations=2)
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_threshold_very_high_forces_retries(self):
        class AlwaysGoodEvaluator(Evaluator):
            async def evaluate(self, task, result):
                from app.evaluation.evaluator import EvaluationResult, QUALITY_GOOD
                return EvaluationResult(score=6.0, success=True, quality=QUALITY_GOOD)

        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(
            planner, executor,
            evaluator=AlwaysGoodEvaluator(),
            quality_threshold=9.0,
        )
        result = await loop.run("搜索资料", max_iterations=2)
        assert result.iterations == 2

    @pytest.mark.asyncio
    async def test_evaluation_with_replanner(self):
        from app.planning.replanner import RePlanner

        class LowEvaluator(Evaluator):
            async def evaluate(self, task, result):
                return EvaluationResult(score=1.0, success=True, quality="poor")

        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(
            planner, executor,
            replanner=RePlanner(),
            evaluator=LowEvaluator(),
            quality_threshold=8.0,
        )
        result = await loop.run("搜索资料", max_iterations=2)
        assert result.iterations == 2