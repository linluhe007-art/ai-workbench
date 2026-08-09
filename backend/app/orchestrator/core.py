"""
Orchestrator 核心引擎
统一调度入口：任务规划 -> Memory查询 -> Agent路由 -> 执行 -> 状态追踪 -> 汇总。
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.memory.service import MemoryContext
from app.orchestrator.executor import StepResult, StepStatus, TaskExecutor
from app.orchestrator.llm_config import create_llm_provider, load_llm_config
from app.orchestrator.llm_provider import LLMProvider
from app.orchestrator.planner import TaskPlan, TaskPlanner, TaskType
from app.orchestrator.router import AgentRouter
from app.orchestrator.task_state import TaskRecord, TaskStateStore, TaskStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OrchestratorResult:
    """Orchestrator 执行结果"""
    task_id: str
    intent: str
    steps: list[StepResult]
    final_output: dict
    memory_context: MemoryContext | None = None
    status: str = "success"
    total_duration_ms: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Orchestrator:
    """
    Orchestrator — AI 调度大脑
    核心流程：任务规划 -> Memory查询 -> Agent路由 -> 执行 -> 状态追踪 -> 汇总
    """

    def __init__(self, memory_service=None, llm_provider: LLMProvider | None = None):
        self.planner = TaskPlanner()
        self.router = AgentRouter()
        self.executor = TaskExecutor(self.router)
        self.memory = memory_service
        self.task_store = TaskStateStore()

        # LLM Provider：优先使用注入的，否则从配置创建
        if llm_provider:
            self.llm = llm_provider
        else:
            config = load_llm_config()
            self.llm = create_llm_provider(config)

    async def run(self, task: str, context: dict | None = None) -> OrchestratorResult:
        """执行完整任务流程"""
        started_at = datetime.now(timezone.utc)
        logger.info("Orchestrator run started", task=task[:80])

        # Step 1: 任务规划
        plan = self.planner.plan(task)

        # 创建任务记录
        record = self.task_store.create(intent=plan.intent, steps_total=len(plan.steps))
        record.update_status(TaskStatus.RUNNING)
        logger.info("Task created", task_id=record.task_id, steps=len(plan.steps))

        # Step 2: 查询 Memory
        memory_ctx = None
        if self.memory and plan.context_query:
            try:
                # 根据首个步骤类型确定 agent_type
                agent_type = self._infer_agent_type(plan)
                memory_ctx = self.memory.get_memory_context(plan.context_query, agent_type=agent_type)
                logger.info("Memory context retrieved", docs=len(memory_ctx.documents), agent_type=agent_type)
            except Exception as e:  # noqa: BLE001 — memory failure is non-critical
                logger.warning("Memory query failed", error=str(e))

        # Step 3: 按依赖顺序执行
        step_results: list[StepResult] = []
        completed_outputs: dict[str, dict] = {}

        for step in plan.steps:
            deps_met = all(completed_outputs.get(dep) is not None for dep in step.depends_on)
            if not deps_met and step.depends_on:
                step_results.append(StepResult(
                    step_id=step.id, status=StepStatus.SKIPPED, agent_id="",
                    error=f"Dependencies not met: {step.depends_on}",
                ))
                continue

            upstream_ctx = {}
            for dep in step.depends_on:
                if dep in completed_outputs:
                    upstream_ctx[dep] = completed_outputs[dep]
            if memory_ctx:
                upstream_ctx["_memory_context"] = {
                    "documents": memory_ctx.documents,
                    "tags": memory_ctx.tags,
                    "related_links": memory_ctx.related_links,
                    "prompt_text": memory_ctx.to_prompt(),
                }

            result = await self.executor.execute(step, upstream_ctx)
            step_results.append(result)

            if result.status == StepStatus.SUCCESS:
                completed_outputs[step.id] = result.output
                record.mark_step_done()
            elif result.status == StepStatus.FAILED:
                record.update_status(TaskStatus.FAILED, error=result.error)

        # Step 4: 汇总
        final_output = self._aggregate_results(plan, step_results)
        completed_at = datetime.now(timezone.utc)
        total_ms = int((completed_at - started_at).total_seconds() * 1000)

        statuses = [r.status for r in step_results]
        if all(s == StepStatus.SUCCESS for s in statuses):
            overall = "success"
            record.update_status(TaskStatus.COMPLETED)
        elif any(s == StepStatus.SUCCESS for s in statuses):
            overall = "partial"
            record.update_status(TaskStatus.COMPLETED)
        else:
            overall = "failed"
            if record.status != TaskStatus.FAILED:
                record.update_status(TaskStatus.FAILED)
        record.result = final_output

        return OrchestratorResult(
            task_id=record.task_id,
            intent=plan.intent,
            steps=step_results,
            final_output=final_output,
            memory_context=memory_ctx,
            status=overall,
            total_duration_ms=total_ms,
            created_at=started_at,
            updated_at=completed_at,
        )

    def _infer_agent_type(self, plan: TaskPlan) -> str | None:
        """从任务计划推断主要 Agent 类型"""
        if not plan.steps:
            return None
        type_map = {
            TaskType.WRITING: "content",
            TaskType.IMAGE: "content",
            TaskType.SEO: "content",
            TaskType.RESEARCH: "research",
            TaskType.ANALYSIS: "research",
        }
        return type_map.get(plan.steps[0].type)

    def _aggregate_results(self, plan: TaskPlan, results: list[StepResult]) -> dict:
        output: dict[str, Any] = {"intent": plan.intent, "steps_summary": []}
        for r in results:
            info = {"step_id": r.step_id, "status": r.status.value, "agent": r.agent_id, "duration_ms": r.duration_ms}
            if r.status == StepStatus.SUCCESS:
                info["output"] = r.output
            elif r.error:
                info["error"] = r.error
            output["steps_summary"].append(info)

        key_map = {"writing": "article", "seo": "seo", "image": "cover", "research": "research", "analysis": "analysis", "chat": "response"}
        for r in results:
            if r.status == StepStatus.SUCCESS and r.step_id in key_map:
                key = key_map[r.step_id]
                output[key] = r.output.get("response", "") if key == "chat" else r.output
        return output

    def get_agent_list(self) -> list[dict]:
        return self.router.list_agents()

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self.task_store.get(task_id)