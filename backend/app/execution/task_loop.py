"""
TaskLoopManager 鈥?鑷富浠诲姟鎵ц寰幆銆?褰撴墽琛屽け璐ユ椂鑷姩閲嶆柊瑙勫垝骞堕噸璇曪紝鐩村埌鎴愬姛鎴栬揪鍒版渶澶ц凯浠ｆ鏁般€?鏁村悎 Planner銆丳ipelineExecutor銆丗eedbackManager銆丷ePlanner銆丠istory銆?Phase 3.17: 鏁村悎 Evaluator 璐ㄩ噺璇勪及銆?Phase 3.18: 闆嗘垚 TraceCollector锛岃褰?iteration/evaluation/replan 浜嬩欢銆?"""

import asyncio
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
    from app.artifacts.extractor import ArtifactExtractor
    from app.workspace.manager import WorkspaceManager

logger = get_logger(__name__)


@dataclass
class IterationRecord:
    """鍗曟杩唬璁板綍"""
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
    寰幆鎵ц缁撴灉銆?    瀛楁锛?    - success: 鏈€缁堟槸鍚︽垚鍔?    - iterations: 鎬昏凯浠ｆ鏁?    - final_result: 鏈€缁?ExecutionResult
    - history: 姣忔杩唬璁板綍
    - task_id: 浠诲姟 ID
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
    鑷富浠诲姟鎵ц寰幆绠＄悊鍣ㄣ€?    娴佺▼锛?    1. Planner 鐢熸垚 TaskPlan
    2. PipelineExecutor 鎵ц锛堝惈 Recovery锛?    3. FeedbackManager 鍒嗘瀽缁撴灉
    4. 鎴愬姛 鈫?杩斿洖
    5. 澶辫触 鈫?RePlanner 閲嶆柊瑙勫垝 鈫?鍥炲埌 2
    6. 杈惧埌 max_iterations 鈫?杩斿洖鏈€鍚庝竴娆＄粨鏋?    鐢ㄦ硶锛?        loop = TaskLoopManager(planner, executor, replanner)
        result = await loop.run("鐮旂┒AI瓒嬪娍骞跺啓鎶ュ憡", max_iterations=3)
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
        cancel_event: asyncio.Event | None = None,
        pause_event: asyncio.Event | None = None,
        artifact_extractor: "ArtifactExtractor | None" = None,
        workspace_manager: "WorkspaceManager | None" = None,
    ):
        self._planner = planner
        self._executor = executor
        self._replanner = replanner
        self._evaluator = evaluator
        self._feedback_mgr = ExecutionFeedbackManager()
        self._history = history or ExecutionHistory()
        self._quality_threshold = quality_threshold
        self._trace = trace_collector
        self._cancel_event = cancel_event
        self._pause_event = pause_event
        self._artifact_extractor = artifact_extractor
        self._workspace = workspace_manager

    def set_trace_collector(self, collector: "TraceCollector"):
        """娉ㄥ叆 TraceCollector 瀹炰緥"""
        self._trace = collector

    async def run(
        self,
        task: str,
        max_iterations: int = 5,
    ) -> LoopResult:
        """
        鎵ц鑷富浠诲姟寰幆銆?        Args:
            task: 鐢ㄦ埛浠诲姟鎻忚堪
            max_iterations: 鏈€澶ц凯浠ｆ鏁?        Returns:
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

            # 鎵ц
            # Check cancel
            if self._cancel_event and self._cancel_event.is_set():
                logger.info("Task loop cancelled", task_id=task_id)
                break

            # Check pause
            if self._pause_event and not self._pause_event.is_set():
                logger.info("Task loop paused", task_id=task_id)
                await self._pause_event.wait()
                logger.info("Task loop resumed", task_id=task_id)

            result = await self._executor.execute_with_recovery(current_plan)

            # 鍒嗘瀽鍙嶉
            feedback = self._feedback_mgr.analyze(result)

            # 璁板綍
            record = IterationRecord(
                iteration=iteration,
                plan=current_plan,
                success=feedback.success,
                status=result.status,
                feedback=feedback,
                duration_ms=result.duration_ms,
            )
            iteration_history.append(record)

            # 璁板綍鍒板巻鍙?
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

            # 璇勪及璐ㄩ噺
            eval_result = None
            if self._evaluator:
                eval_result = await self._evaluator.evaluate(task, result)
                logger.info("Evaluation", score=eval_result.score, quality=eval_result.quality)

                # Trace: evaluation score
                if self._trace:
                    self._trace.metric(trace_id, task_id, "loop", "eval_score", eval_result.score)

            # 鎴愬姛涓旇川閲忚揪鏍?鈫?杩斿洖
            if feedback.success and (not eval_result or eval_result.score >= self._quality_threshold):
                logger.info("Task loop succeeded", task_id=task_id, iterations=iteration)

                # Extract artifacts and save to workspace
                await self._extract_and_save_artifacts(task_id, result)

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

            # 鏈€鍚庝竴娆¤凯浠?鈫?杩斿洖澶辫触
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

            # 閲嶆柊瑙勫垝
            if self._replanner:
                # Trace: replan
                if self._trace:
                    self._trace.metric(trace_id, task_id, "loop", "replan", iteration)

                current_plan = await self._replanner.replan(task, current_plan, feedback)
                logger.info("Replanned", iteration=iteration + 1, steps=len(current_plan.steps))
            else:
                logger.info("No replanner, retrying same plan", iteration=iteration + 1)

        # 涓嶅簲鍒拌揪杩欓噷
        return LoopResult(
            success=False,
            iterations=max_iterations,
            history=iteration_history,
            task_id=task_id,
        )

    async def _extract_and_save_artifacts(self, task_id: str, result) -> None:
        """Extract artifacts from execution result and save to workspace."""
        if not self._artifact_extractor or not self._workspace:
            return
        try:
            artifacts = await self._artifact_extractor.extract(task_id, result)
            if artifacts:
                # Ensure workspace exists
                self._workspace.create_workspace(task_id)
                for artifact in artifacts:
                    from app.workspace.models import WorkspaceItem
                    item = WorkspaceItem(
                        name=artifact.get("name", "unnamed"),
                        type=artifact.get("type", "text"),
                        content=artifact.get("content", ""),
                        owner=artifact.get("metadata", {}).get("created_by", "system"),
                        metadata=artifact.get("metadata", {}),
                    )
                    self._workspace.add_item(task_id, item)
                logger.info("Artifacts saved to workspace", task_id=task_id, count=len(artifacts))
        except Exception:  # noqa: BLE001
            logger.exception("Failed to extract/save artifacts", task_id=task_id)

    @property
    def history(self) -> ExecutionHistory:
        return self._history