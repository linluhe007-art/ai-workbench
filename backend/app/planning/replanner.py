"""
RePlanner — 重新规划器。

当执行失败时，根据失败信息重新生成 TaskPlan。
尝试替换失败步骤的 Agent，保持原任务 intent。
"""

import copy
from typing import TYPE_CHECKING

from app.orchestrator.planner import TaskPlan, TaskStep
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.selector import AgentSelector
    from app.execution.feedback import FeedbackResult

logger = get_logger(__name__)


class RePlanner:
    """
    重新规划器。

    职责：
    - 根据失败步骤重新生成 TaskPlan
    - 使用 AgentSelector 替换失败 Agent
    - 保持原任务 intent

    用法：
        replanner = RePlanner(agent_selector)
        new_plan = await replanner.replan(task, old_plan, feedback)
    """

    def __init__(self, agent_selector: "AgentSelector | None" = None):
        self._selector = agent_selector

    async def replan(
        self,
        task: str,
        old_plan: TaskPlan,
        feedback: "FeedbackResult",
    ) -> TaskPlan:
        """
        根据失败信息重新规划。
        Args:
            task: 原始任务描述
            old_plan: 原始 TaskPlan
            feedback: 执行反馈
        Returns:
            新的 TaskPlan
        """
        if not feedback.failed_steps:
            # 没有失败步骤，返回原 plan
            return old_plan

        new_steps = []
        replaced = {}

        for step in old_plan.steps:
            if step.id in feedback.failed_steps:
                new_step = self._try_replace_agent(step, task)
                new_steps.append(new_step)
                if new_step.agent_hint != step.agent_hint:
                    replaced[step.id] = new_step.agent_hint
            else:
                new_steps.append(copy.deepcopy(step))

        if replaced:
            logger.info("Replan: agents replaced", replaced=replaced)
        else:
            logger.info("Replan: no agents replaced, retrying with same plan")

        return TaskPlan(
            intent=old_plan.intent,
            steps=new_steps,
            context_query=old_plan.context_query,
        )

    def _try_replace_agent(self, step: TaskStep, task: str) -> TaskStep:
        """尝试替换失败步骤的 Agent"""
        if not self._selector:
            return copy.deepcopy(step)

        capability = step.params.get("capability", step.type.value)
        new_agent = self._selector.select(
            capability,
            context={"task_pattern": task},
        )

        if new_agent and new_agent != step.agent_hint:
            new_step = copy.deepcopy(step)
            new_step.agent_hint = new_agent
            return new_step

        return copy.deepcopy(step)