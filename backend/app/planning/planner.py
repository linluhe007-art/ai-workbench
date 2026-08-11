"""
Planner — 统一规划接口。

封装 WorkflowGenerator，提供简洁的 plan() 方法。
作为 Orchestrator 和 PipelineExecutor 之间的规划层。

当前：规则型规划（关键词匹配）
未来：可替换为 LLM 驱动规划
"""

from typing import TYPE_CHECKING

from app.orchestrator.planner import TaskPlan
from app.planning.workflow import WorkflowGenerator
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry

logger = get_logger(__name__)


class Planner:
    """
    统一规划器。

    职责：
    - 接收用户任务描述
    - 委托 WorkflowGenerator 生成 TaskPlan
    - 为未来 LLM 规划预留扩展点

    用法：
        planner = Planner(workflow_generator)
        plan = planner.plan("研究AI趋势并写报告")
    """

    def __init__(self, workflow_generator: WorkflowGenerator):
        self._workflow = workflow_generator

    def plan(self, task: str) -> TaskPlan:
        """
        生成任务计划。
        Args:
            task: 用户任务描述
        Returns:
            TaskPlan（带 DAG 依赖）
        Raises:
            ValueError: 任务为空
        """
        logger.info("Planner planning task", task=task[:80])
        plan = self._workflow.generate(task)
        logger.info("Plan generated", steps=len(plan.steps), intent=plan.intent[:50])
        return plan

    @classmethod
    def from_registry(cls, registry: "AgentRegistry | None" = None) -> "Planner":
        """
        便捷工厂：从 AgentRegistry 创建 Planner。
        Args:
            registry: AgentRegistry 实例（可选）
        Returns:
            Planner 实例
        """
        workflow = WorkflowGenerator(agent_registry=registry)
        return cls(workflow)