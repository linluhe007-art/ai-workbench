"""
Pipeline 执行引擎
接收 TaskPlan，按 DAG 依赖顺序执行所有步骤。
支持 Memory 上下文注入（执行前查询）和结果回写（执行后存储）。
Phase 3.8 升级：支持同层并行执行（asyncio.gather）。
Phase 3.18: 集成 TraceCollector，记录 step 开始/结束/失败事件。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
from typing import TYPE_CHECKING

from app.orchestrator.planner import TaskPlan, TaskStep
from app.orchestrator.executor import StepResult, StepStatus
from app.agents.context import AgentContext
from app.agents.mock_agent import MockAgent
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.base import BaseAgent
    from app.memory.service import MemoryService
    from app.memory.experience import ExperienceMemory

logger = get_logger(__name__)


@dataclass
class ExecutionResult:
    """Pipeline 完整执行结果"""
    plan_intent: str
    step_results: dict[str, StepResult]
    status: str = "success"
    memory_contexts: dict[str, AgentContext] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.step_results.values() if r.status == StepStatus.SUCCESS)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.step_results.values() if r.status == StepStatus.FAILED)

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.step_results.values() if r.status == StepStatus.SKIPPED)

    def to_dict(self) -> dict:
        return {
            "plan_intent": self.plan_intent,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "success": self.success_count,
            "failed": self.failed_count,
            "skipped": self.skipped_count,
            "steps": {
                sid: {
                    "status": r.status.value,
                    "agent_id": r.agent_id,
                    "duration_ms": r.duration_ms,
                    "output": r.output if r.status == StepStatus.SUCCESS else None,
                    "error": r.error,
                }
                for sid, r in self.step_results.items()
            },
        }


class PipelineExecutor:
    """
    Pipeline 执行引擎
    按 DAG 拓扑顺序执行 TaskPlan 中的所有步骤。
    Phase 3.8: 同层无依赖步骤通过 asyncio.gather 并行执行。
    支持 Memory 上下文注入和结果回写。
    Phase 3.18: 可选 TraceCollector 追踪。
    """

    def __init__(
        self,
        agent_map: dict[str, "BaseAgent | MockAgent"] | None = None,
        memory_service: "MemoryService | None" = None,
        experience: "ExperienceMemory | None" = None,
        trace_collector: "TraceCollector | None" = None,
    ):
        self._agent_map = agent_map or {}
        self._memory = memory_service
        self._experience = experience
        self._trace = trace_collector

    def set_trace_collector(self, collector: "TraceCollector"):
        """注入 TraceCollector 实例"""
        self._trace = collector

    async def execute(self, plan: TaskPlan) -> ExecutionResult:
        """执行完整 TaskPlan（DAG 并行调度）"""
        started_at = datetime.now(timezone.utc)
        results: dict[str, StepResult] = {}
        memory_contexts: dict[str, AgentContext] = {}

        trace_id = self._trace.generate_trace_id() if self._trace else ""
        task_id = plan.intent

        # Trace: pipeline start
        if self._trace:
            self._trace.start(trace_id, task_id, "executor", metadata={"intent": plan.intent, "steps": len(plan.steps)})

        levels = self._topological_levels(plan.steps)
        logger.info(
            "Pipeline execution started",
            intent=plan.intent,
            steps=len(plan.steps),
            levels=len(levels),
        )

        for level_idx, level_steps in enumerate(levels):
            # 过滤掉依赖已失败的步骤
            runnable = []
            for step in level_steps:
                if self._has_failed_deps(step, results):
                    results[step.id] = StepResult(
                        step_id=step.id,
                        status=StepStatus.SKIPPED,
                        agent_id="",
                        error=f"Dependency failed: {step.depends_on}",
                    )
                    logger.info("Step skipped", step_id=step.id)
                else:
                    runnable.append(step)

            if not runnable:
                continue

            if len(runnable) == 1:
                # 单步骤直接执行
                step = runnable[0]
                upstream_output = self._collect_upstream(step, results)
                ctx = await self._build_context(step, plan, upstream_output)
                memory_contexts[step.id] = ctx
                result = await self._execute_step(step, ctx, trace_id, task_id)
                results[step.id] = result
                if result.status == StepStatus.SUCCESS:
                    await self._write_back_memory(step, result)
            else:
                # 多步骤并行执行
                logger.info(
                    "Parallel execution",
                    level=level_idx,
                    steps=[s.id for s in runnable],
                )
                coros = []
                for step in runnable:
                    upstream_output = self._collect_upstream(step, results)
                    ctx = await self._build_context(step, plan, upstream_output)
                    memory_contexts[step.id] = ctx
                    coros.append(self._execute_step(step, ctx, trace_id, task_id))

                level_results = await asyncio.gather(*coros)
                for step, result in zip(runnable, level_results):
                    results[step.id] = result
                    if result.status == StepStatus.SUCCESS:
                        await self._write_back_memory(step, result)

        completed_at = datetime.now(timezone.utc)
        duration = int((completed_at - started_at).total_seconds() * 1000)
        status = self._compute_status(results)

        # Trace: pipeline end
        if self._trace:
            self._trace.end(
                trace_id, task_id, "executor",
                duration_ms=duration,
                metadata={"status": status, "success_count": sum(1 for r in results.values() if r.status == StepStatus.SUCCESS)},
            )

        logger.info(
            "Pipeline execution completed",
            intent=plan.intent,
            status=status,
            duration_ms=duration,
        )

        return ExecutionResult(
            plan_intent=plan.intent,
            step_results=results,
            status=status,
            memory_contexts=memory_contexts,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration,
        )

    async def execute_with_recovery(self, plan: TaskPlan, max_retries: int = 1) -> ExecutionResult:
        """
        带恢复的执行：先执行，再分析反馈。
        如果失败可重试，自动选择替代 Agent。
        Args:
            plan: TaskPlan
            max_retries: 最大重试次数 (0=不重试, 1=默认重试一次)
        """
        from app.execution.feedback import ExecutionFeedbackManager
        from app.execution.recovery import ExecutionRecoveryManager

        current_plan = plan
        last_result = None

        for attempt in range(max_retries + 1):
            result = await self.execute(current_plan)
            last_result = result
            feedback = ExecutionFeedbackManager().analyze(result)

            if feedback.success:
                return result

            # 已达最大重试次数
            if attempt >= max_retries:
                logger.info("Max retries reached", attempts=attempt + 1)
                return result

            # 尝试恢复
            recovery = ExecutionRecoveryManager()
            recovery_result = await recovery.recover(plan.intent, current_plan, result, feedback)

            if not recovery_result.recovered:
                logger.info("Recovery not possible, returning last result", action=recovery_result.action)
                return result

            # 可恢复：使用新 plan 或重试原 plan
            if recovery_result.new_plan:
                logger.info("Recovery: retrying with new plan", action=recovery_result.action, attempt=attempt + 1)
                current_plan = recovery_result.new_plan
            else:
                logger.info("Recovery: retrying same plan", action=recovery_result.action, attempt=attempt + 1)
                # current_plan 保持不变，直接重试

        return last_result

    async def _build_context(
        self, step: TaskStep, plan: TaskPlan, upstream_output: dict
    ) -> AgentContext:
        """构建 AgentContext，注入 Memory + upstream"""
        memory_docs = []
        if self._memory:
            try:
                ctx = await self._memory.get_context(step.description)
                memory_docs = ctx.get("documents", []) if isinstance(ctx, dict) else []
            except Exception:  # noqa: BLE001 memory failure should not block execution
                logger.warning("Memory context fetch failed", step=step.id)

        return AgentContext(
            task=step.description,
            upstream=upstream_output,
            memory=memory_docs,
            metadata={"plan_intent": plan.intent, "step_id": step.id},
        )

    async def _write_back_memory(self, step: TaskStep, result: StepResult):
        """执行成功后将结果回写到 Memory/Experience"""
        if self._experience:
            try:
                self._experience.record_experience(
                    task_pattern=step.description,
                    agents=[result.agent_id],
                    result={"success": True, "output_keys": list(result.output.keys()) if isinstance(result.output, dict) else []},
                    metadata={"step_id": step.id, "duration_ms": result.duration_ms},
                )
            except Exception:  # noqa: BLE001 write-back failure is non-fatal
                logger.warning("Memory write-back failed", step=step.id)

    async def _execute_step(self, step: TaskStep, ctx: AgentContext, trace_id: str = "", task_id: str = "") -> StepResult:
        agent = self._resolve_agent(step)
        started_at = datetime.now(timezone.utc)

        # Trace: step start
        if self._trace:
            self._trace.start(trace_id, task_id, "executor", metadata={"step_id": step.id, "agent_id": agent.id})

        try:
            output = await agent.execute_step(step, ctx)
            completed_at = datetime.now(timezone.utc)
            duration = int((completed_at - started_at).total_seconds() * 1000)

            logger.info("Step completed", step_id=step.id, agent=agent.id, duration_ms=duration)

            # Trace: step end
            if self._trace:
                self._trace.end(trace_id, task_id, "executor", duration_ms=duration, metadata={"step_id": step.id, "agent_id": agent.id, "success": True})

            return StepResult(
                step_id=step.id,
                status=StepStatus.SUCCESS,
                agent_id=agent.id,
                output=output,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration,
            )
        except Exception as e:  # noqa: BLE001 step failure is recorded, not fatal
            completed_at = datetime.now(timezone.utc)
            duration = int((completed_at - started_at).total_seconds() * 1000)

            logger.warning("Step failed", step_id=step.id, error=str(e))

            # Trace: step error
            if self._trace:
                self._trace.error(trace_id, task_id, "executor", error=str(e), metadata={"step_id": step.id, "agent_id": agent.id})

            return StepResult(
                step_id=step.id,
                status=StepStatus.FAILED,
                agent_id=agent.id,
                error=str(e),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration,
            )

    def _has_failed_deps(self, step: TaskStep, results: dict[str, StepResult]) -> bool:
        for dep_id in step.depends_on:
            dep_result = results.get(dep_id)
            if dep_result is None or dep_result.status in (StepStatus.FAILED, StepStatus.SKIPPED):
                return True
        return False

    def _collect_upstream(self, step: TaskStep, results: dict[str, StepResult]) -> dict:
        upstream = {}
        for dep_id in step.depends_on:
            if dep_id in results and results[dep_id].status == StepStatus.SUCCESS:
                upstream[dep_id] = results[dep_id].output
        return upstream

    def _resolve_agent(self, step: TaskStep) -> "BaseAgent | MockAgent":
        if step.id in self._agent_map:
            return self._agent_map[step.id]
        if step.type.value in self._agent_map:
            return self._agent_map[step.type.value]
        if "default" in self._agent_map:
            return self._agent_map["default"]
        return MockAgent(agent_id=f"auto-mock-{step.id}")

    @staticmethod
    def _topological_sort(steps: list[TaskStep]) -> list[TaskStep]:
        """Flat topological sort (backward compatible)."""
        step_map = {s.id: s for s in steps}
        in_degree: dict[str, int] = {s.id: 0 for s in steps}
        graph: dict[str, list[str]] = defaultdict(list)

        for s in steps:
            for dep in s.depends_on:
                if dep in step_map:
                    graph[dep].append(s.id)
                    in_degree[s.id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        ordered: list[TaskStep] = []

        while queue:
            sid = queue.pop(0)
            ordered.append(step_map[sid])
            for next_id in graph[sid]:
                in_degree[next_id] -= 1
                if in_degree[next_id] == 0:
                    queue.append(next_id)

        return ordered

    @staticmethod
    def _topological_levels(steps: list[TaskStep]) -> list[list[TaskStep]]:
        """
        将步骤按拓扑层级分组。
        Level 0: 无依赖的步骤
        Level 1: 依赖全部在 Level 0 的步骤
        ...
        同层步骤可并行执行。
        """
        step_map = {s.id: s for s in steps}
        in_degree: dict[str, int] = {s.id: 0 for s in steps}
        graph: dict[str, list[str]] = defaultdict(list)

        for s in steps:
            for dep in s.depends_on:
                if dep in step_map:
                    graph[dep].append(s.id)
                    in_degree[s.id] += 1

        levels: list[list[TaskStep]] = []
        current = [sid for sid, deg in in_degree.items() if deg == 0]

        while current:
            level = [step_map[sid] for sid in current]
            levels.append(level)
            next_level = []
            for sid in current:
                for next_id in graph[sid]:
                    in_degree[next_id] -= 1
                    if in_degree[next_id] == 0:
                        next_level.append(next_id)
            current = next_level

        return levels

    @staticmethod
    def _compute_status(results: dict[str, StepResult]) -> str:
        all_statuses = [r.status for r in results.values()]
        if all(s == StepStatus.SUCCESS for s in all_statuses):
            return "success"
        elif any(s == StepStatus.SUCCESS for s in all_statuses):
            return "partial"
        return "failed"