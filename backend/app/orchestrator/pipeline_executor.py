"""
Pipeline 执行引擎
接收 TaskPlan，按 DAG 依赖顺序执行所有步骤。
支持：串行/并行分支、失败跳过依赖、状态追踪。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict

from app.orchestrator.planner import TaskPlan, TaskStep
from app.orchestrator.executor import StepResult, StepStatus
from app.agents.mock_agent import MockAgent
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionResult:
    """Pipeline 完整执行结果"""
    plan_intent: str
    step_results: dict[str, StepResult]  # step_id -> StepResult
    status: str = "success"              # success / partial / failed
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
    规则：
    - 依赖全部成功 → 执行当前步骤
    - 任一依赖失败 → 当前步骤标记 SKIPPED
    - Agent 执行失败 → 标记 FAILED，后续依赖被 SKIPPED
    """

    def __init__(self, agent_map: dict[str, MockAgent] | None = None):
        """
        Args:
            agent_map: step_id 或 task_type -> MockAgent 映射
                       查找顺序：step.id → step.type.value → "default"
        """
        self._agent_map: dict[str, MockAgent] = agent_map or {}

    async def execute(self, plan: TaskPlan) -> ExecutionResult:
        """
        执行完整 TaskPlan
        Args:
            plan: 任务计划
        Returns:
            ExecutionResult
        """
        started_at = datetime.now(timezone.utc)
        results: dict[str, StepResult] = {}
        step_map: dict[str, TaskStep] = {s.id: s for s in plan.steps}

        # 拓扑排序
        ordered = self._topological_sort(plan.steps)

        logger.info("Pipeline execution started", intent=plan.intent, steps=len(ordered))

        for step in ordered:
            # 检查依赖
            dep_failed = False
            for dep_id in step.depends_on:
                dep_result = results.get(dep_id)
                if dep_result is None:
                    # 依赖未执行（不应该发生，拓扑排序保证顺序）
                    dep_failed = True
                    break
                if dep_result.status in (StepStatus.FAILED, StepStatus.SKIPPED):
                    dep_failed = True
                    break

            if dep_failed:
                results[step.id] = StepResult(
                    step_id=step.id,
                    status=StepStatus.SKIPPED,
                    agent_id="",
                    error=f"Dependency failed: {step.depends_on}",
                )
                logger.info("Step skipped", step_id=step.id)
                continue

            # 收集上游输出作为上下文
            upstream_output = {}
            for dep_id in step.depends_on:
                if dep_id in results and results[dep_id].status == StepStatus.SUCCESS:
                    upstream_output[dep_id] = results[dep_id].output

            # 执行步骤
            result = await self._execute_step(step, upstream_output)
            results[step.id] = result

        # 计算整体状态
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        all_statuses = [r.status for r in results.values()]
        if all(s == StepStatus.SUCCESS for s in all_statuses):
            overall = "success"
        elif any(s == StepStatus.SUCCESS for s in all_statuses):
            overall = "partial"
        else:
            overall = "failed"

        return ExecutionResult(
            plan_intent=plan.intent,
            step_results=results,
            status=overall,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )

    async def _execute_step(self, step: TaskStep, upstream_output: dict) -> StepResult:
        """执行单个步骤"""
        agent = self._resolve_agent(step)
        started_at = datetime.now(timezone.utc)

        try:
            output = await agent.execute(step)
            completed_at = datetime.now(timezone.utc)
            duration = int((completed_at - started_at).total_seconds() * 1000)

            logger.info("Step completed", step_id=step.id, agent=agent.id, duration_ms=duration)

            return StepResult(
                step_id=step.id,
                status=StepStatus.SUCCESS,
                agent_id=agent.id,
                output=output,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration,
            )
        except Exception as e:  # noqa: BLE001 — step failure is recorded, not fatal
            completed_at = datetime.now(timezone.utc)
            duration = int((completed_at - started_at).total_seconds() * 1000)

            logger.warning("Step failed", step_id=step.id, error=str(e))

            return StepResult(
                step_id=step.id,
                status=StepStatus.FAILED,
                agent_id=agent.id,
                error=str(e),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration,
            )

    def _resolve_agent(self, step: TaskStep) -> MockAgent:
        """查找步骤对应的 Agent"""
        # 优先按 step.id 查找
        if step.id in self._agent_map:
            return self._agent_map[step.id]
        # 按 task_type 查找
        if step.type.value in self._agent_map:
            return self._agent_map[step.type.value]
        # 默认
        if "default" in self._agent_map:
            return self._agent_map["default"]
        # 没有配置则返回通用 MockAgent
        return MockAgent(agent_id=f"auto-mock-{step.id}")

    @staticmethod
    def _topological_sort(steps: list[TaskStep]) -> list[TaskStep]:
        """
        拓扑排序：按依赖关系排列步骤顺序。
        保证每个步骤在其所有依赖之后执行。
        """
        step_map = {s.id: s for s in steps}
        in_degree: dict[str, int] = {s.id: 0 for s in steps}
        graph: dict[str, list[str]] = defaultdict(list)

        for s in steps:
            for dep in s.depends_on:
                if dep in step_map:
                    graph[dep].append(s.id)
                    in_degree[s.id] += 1

        # Kahn 算法
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