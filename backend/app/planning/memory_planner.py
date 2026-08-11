"""
MemoryAwarePlanner — 记忆增强规划器。

在规划前先检索历史经验，为 Planner 提供决策参考。
不替换原 Planner，而是在其上层封装。
"""

from typing import TYPE_CHECKING

from app.memory.context import PlanningMemoryContext
from app.memory.experience import ExperienceMemory
from app.memory.retrieval import MemoryRetriever
from app.orchestrator.planner import TaskPlan
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.planning.planner import Planner

logger = get_logger(__name__)


class MemoryAwarePlanner:
    """
    记忆增强规划器。

    流程：
    1. 用 MemoryRetriever 检索历史经验
    2. 构建 PlanningMemoryContext
    3. 调用原 Planner 生成 TaskPlan
    4. 将 MemoryContext 附加到 Plan（通过 context_query）

    用法：
        planner = MemoryAwarePlanner(inner_planner, experience_memory)
        plan = await planner.plan("研究AI趋势并写报告")
    """

    def __init__(
        self,
        inner_planner: "Planner",
        experience_memory: ExperienceMemory | None = None,
        retriever: MemoryRetriever | None = None,
    ):
        self._planner = inner_planner
        self._experience = experience_memory or ExperienceMemory()
        self._retriever = retriever or MemoryRetriever()

    async def plan(self, task: str) -> tuple[TaskPlan, PlanningMemoryContext]:
        """
        记忆增强规划。
        Args:
            task: 用户任务描述
        Returns:
            (TaskPlan, PlanningMemoryContext)
        """
        # Step 1: 检索历史经验
        memory_ctx = self._build_memory_context(task)

        logger.info(
            "Memory-aware planning",
            task=task[:50],
            has_history=memory_ctx.has_history,
            similar=len(memory_ctx.similar_tasks),
            success_rate=memory_ctx.historical_success_rate,
        )

        # Step 2: 调用原 Planner
        plan = self._planner.plan(task)

        return plan, memory_ctx

    def _build_memory_context(self, task: str) -> PlanningMemoryContext:
        """从历史经验构建记忆上下文"""
        # 查询相似任务
        similar = self._experience.query_experience(task, limit=5)

        # 推荐 Agent
        recommended = self._experience.get_best_agents(task, limit=3)

        # 历史成功率
        success_rate = self._experience.get_success_rate(task)

        # 生成警告
        warnings = self._generate_warnings(similar, success_rate)

        return PlanningMemoryContext(
            similar_tasks=similar,
            recommended_agents=recommended,
            historical_success_rate=success_rate,
            warnings=warnings,
        )

    @staticmethod
    def _generate_warnings(similar: list[dict], success_rate: float) -> list[str]:
        """根据历史经验生成警告"""
        warnings = []

        if similar and success_rate < 0.3:
            warnings.append(f"Historical success rate is low ({success_rate:.0%}), consider reviewing the plan")

        failure_agents = set()
        for rec in similar:
            if not rec.get("success"):
                failure_agents.update(rec.get("agents", []))
        if failure_agents:
            warnings.append(f"Agents {failure_agents} have failure history on similar tasks")

        return warnings

    @property
    def experience_memory(self) -> ExperienceMemory:
        return self._experience