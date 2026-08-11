"""
TaskLoopManager — 自主任务执行循环。
当执行失败时自动重新规划并重试，直到成功或达到最大迭代次数。
整合 Planner、PipelineExecutor、FeedbackManager、RePlanner、History。
Phase 3.17: 整合 Evaluator 质量评估。
Phase 3.18: 集成 TraceCollector，记录 iteration/evaluation/replan 事件。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.evaluation.evaluator import EvaluationResult, Evaluator
from app.execution.feedback import ExecutionFeedbackManager, FeedbackResult
from app.execution.history import ExecutionHistory
from app.orchestrator.planner import TaskPlan
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.orchestrator.pipeline_executor import PipelineExecutor
    from app.planning.planner import Planner
    from app.planning.replanner import RePlanner
    from app.evaluation.evaluator import Evaluator as EvaluatorType
    from app.observability.collector import TraceCollector

logger = get_logger(__name__)


@dataclass
class IterationRecord:
    """单次迭代记录"""
    iteration: int
    plan: TaskPlan
    success: bool
    status: str
    feedback: FeedbackResult | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "success": self.success,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "step_count": len(self.plan.steps),
        }


@dataclass
class LoopResult:
    """
    循环执行结果。
    字段：
    - success: 最终是否成功
    - iterations: 总迭代次数
    - final_result: 最终 ExecutionResult
    - history: 每次迭代记录
    - task_id: 任务 ID
    """
    success: bool
    iterations: int
    final_result: any = None
    history: list[IterationRecord] = field(default_factory=list)
    task_id: str = ""
    evaluation: "EvaluationResult | None" = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "iterations": self.iterations,
            "task_id": self.task_id,
            "history": [r.to_dict() for r in self.history],
        }


class TaskLoopManager:
    """
    自主任务执行循环管理器。
    流程：
    1. Planner 生成 TaskPlan
    2. PipelineExecutor 执行（含 Recovery）
    3. FeedbackManager 分析结果
    4. 成功 → 返回
    5. 失败 → RePlanner 重新规划 → 回到 2
    6. 达到 max_iterations → 返回最后一次结果
    用法：
        loop = TaskLoopManager(planner, executor, replanner)
        result = await loop.run("研究AI趋势并写报告", max_iterations=3)
    """

    def __init__(
        self,
        planner: "Planner",
        executor: "PipelineExecutor",
        replanner: "RePlanner | None" = None,
        history: ExecutionHistory | None = None,
        evaluator: "EvaluatorType | None" = None,
        quality_threshold: float = 7.0,
        trace_collector: "TraceCollector | None" = None,
    ):
        self._planner = planner
        self._executor = executor
        self._replanner = replanner
        self._evaluator = evaluator
        self._feedback_mgr = ExecutionFeedbackManager()
        self._history = history or ExecutionHistory()
        self._quality_threshold = quality_threshold
        self._trace = trace_collector

    def set_trace_collector(self, collector: "TraceCollector"):
        """注入 TraceCollector 实例"""
        self._trace = collector

    async def run(
        self,
        task: str,
        max_iterations: int = 5,
    ) -> LoopResult:
        """
        执行自主任务循环。
        Args:
            task: 用户任务描述
            max_iterations: 最大迭代次数
        Returns:
            LoopResult
        """
        from app.observability.collector import TraceCollector

        task_id = ExecutionHistory.generate_task_id()
        trace_id = TraceCollector.generate_trace_id() if self._trace else ""

        current_plan = self._planner.plan(task)
        iteration_history: list[IterationRecord] = []

        logger.info("Task loop started", task=task[:50], task_id=task_id, max_iter=max_iterations)

        # Trace: loop start
        if self._trace:
            self._trace.start(trace_id, task_id, "loop", metadata={"task": task, "max_iterations": max_iterations})

        for iteration in range(1, max_iterations + 1):
            # Trace: iteration metric
            if self._trace:
                self._trace.metric(trace_id, task_id, "loop", "iteration", iteration)

            # 执行
            result = await self._executor.execute_with_recovery(current_plan)

            # 分析反馈
            feedback = self._feedback_mgr.analyze(result)

            # 记录
            record = IterationRecord(
                iteration=iteration,
                plan=current_plan,
                success=feedback.success,
                status=result.status,
                feedback=feedback,
                duration_ms=result.duration_ms,
            )
            iteration_history.append(record)

            # 记录到历史
            self._history.record(
                task_id=task_id,
                iteration=iteration,
                plan_intent=current_plan.intent,
                step_count=len(current_plan.steps),
                success=feedback.success,
                status=result.status,
                duration_ms=result.duration_ms,
                failed_steps=feedback.failed_steps,
            )

            # 评估质量
            eval_result = None
            if self._evaluator:
                eval_result = await self._evaluator.evaluate(task, result)
                logger.info("Evaluation", score=eval_result.score, quality=eval_result.quality)

                # Trace: evaluation score
                if self._trace:
                    self._trace.metric(trace_id, task_id, "loop", "eval_score", eval_result.score)

            # 成功且质量达标 → 返回
            if feedback.success and (not eval_result or eval_result.score >= self._quality_threshold):
                logger.info("Task loop succeeded", task_id=task_id, iterations=iteration)

                # Trace: loop end (success)
                if self._trace:
                    self._trace.end(trace_id, task_id, "loop", duration_ms=result.duration_ms, metadata={"success": True, "iterations": iteration})

                return LoopResult(
                    success=True,
                    iterations=iteration,
                    final_result=result,
                    history=iteration_history,
                    task_id=task_id,
                    evaluation=eval_result,
                )

            # 最后一次迭代 → 返回失败
            if iteration >= max_iterations:
                logger.info("Task loop max iterations reached", task_id=task_id, iterations=iteration)

                # Trace: loop end (max iterations)
                if self._trace:
                    self._trace.end(trace_id, task_id, "loop", duration_ms=result.duration_ms, metadata={"success": False, "iterations": iteration, "reason": "max_iterations"})

                return LoopResult(
                    success=False,
                    iterations=iteration,
                    final_result=result,
                    history=iteration_history,
                    task_id=task_id,
                )

            # 重新规划
            if self._replanner:
                # Trace: replan
                if self._trace:
                    self._trace.metric(trace_id, task_id, "loop", "replan", iteration)

                current_plan = await self._replanner.replan(task, current_plan, feedback)
                logger.info("Replanned", iteration=iteration + 1, steps=len(current_plan.steps))
            else:
                logger.info("No replanner, retrying same plan", iteration=iteration + 1)

        # 不应到达这里
        return LoopResult(
            success=False,
            iterations=max_iterations,
            history=iteration_history,
            task_id=task_id,
        )

    @property
    def history(self) -> ExecutionHistory:
        return self._history