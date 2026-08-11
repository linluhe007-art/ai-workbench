"""
ExecutionRecoveryManager — 执行恢复管理器。

根据 FeedbackResult 决定恢复策略：
- 无需恢复（成功）
- 直接重试（retryable 错误）
- 替换 Agent 后重试（agent 失败）
- 终止（不可恢复）
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.selector import AgentSelector
    from app.execution.feedback import FeedbackResult
    from app.orchestrator.pipeline_executor import ExecutionResult
    from app.orchestrator.planner import TaskPlan

logger = get_logger(__name__)


@dataclass
class RecoveryResult:
    """
    恢复结果。

    字段：
    - recovered: 是否已恢复（可继续执行）
    - action: 恢复动作 (none / retry / retry_agent / abort)
    - new_plan: 新的执行计划（仅 retry_agent 时非 None）
    - reason: 恢复原因
    - replaced_agents: 被替换的 agent 映射 {step_id: new_agent_id}
    """
    recovered: bool
    action: str
    reason: str
    new_plan: "TaskPlan | None" = None
    replaced_agents: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "recovered": self.recovered,
            "action": self.action,
            "reason": self.reason,
            "has_new_plan": self.new_plan is not None,
            "replaced_agents": self.replaced_agents,
        }


class ExecutionRecoveryManager:
    """
    执行恢复管理器。

    职责：
    - 根据 FeedbackResult 决定恢复策略
    - 尝试替换失败步骤的 Agent
    - 生成新的 TaskPlan（如果需要）

    恢复优先级：
    1. 成功 → 不恢复
    2. retryable → 直接重试原 plan
    3. agent 失败 → 替换 agent 后重试
    4. 不可恢复 → 终止
    """

    def __init__(self, agent_selector: "AgentSelector | None" = None):
        self._selector = agent_selector

    async def recover(
        self,
        task: str,
        plan: "TaskPlan",
        result: "ExecutionResult",
        feedback: "FeedbackResult",
    ) -> RecoveryResult:
        """
        决定恢复策略。
        Args:
            task: 原始任务描述
            plan: 原始 TaskPlan
            result: 执行结果
            feedback: 反馈结果
        Returns:
            RecoveryResult
        """
        # 规则 1: 成功无需恢复
        if feedback.success:
            return RecoveryResult(
                recovered=True,
                action="none",
                reason="Execution succeeded, no recovery needed",
            )

        # 规则 2: retryable → 直接重试
        if feedback.retryable:
            logger.info("Recovery: retry", failed=feedback.failed_steps)
            return RecoveryResult(
                recovered=True,
                action="retry",
                reason=f"Retryable error in steps: {feedback.failed_steps}",
            )

        # 规则 3: 尝试替换失败步骤的 Agent
        if feedback.failed_steps and self._selector:
            recovery = self._try_replace_agents(plan, feedback)
            if recovery.recovered:
                return recovery

        # 规则 4: 不可恢复
        logger.info("Recovery: abort", reason=feedback.reason)
        return RecoveryResult(
            recovered=False,
            action="abort",
            reason=f"Cannot recover: {feedback.reason}",
        )

    def _try_replace_agents(
        self,
        plan: "TaskPlan",
        feedback: "FeedbackResult",
    ) -> RecoveryResult:
        """尝试替换失败步骤的 Agent"""
        import copy

        new_steps = []
        replaced = {}
        any_replaced = False

        for step in plan.steps:
            if step.id in feedback.failed_steps:
                # 尝试找到替代 Agent
                capability = step.params.get("capability", step.type.value)
                new_agent = self._selector.select(capability) if self._selector else None

                if new_agent and new_agent != step.agent_hint:
                    # 找到不同 Agent → 替换
                    new_step = copy.copy(step)
                    new_step.agent_hint = new_agent
                    new_steps.append(new_step)
                    replaced[step.id] = new_agent
                    any_replaced = True
                    logger.info(
                        "Agent replaced for retry",
                        step_id=step.id,
                        old=step.agent_hint,
                        new=new_agent,
                    )
                else:
                    new_steps.append(step)
            else:
                new_steps.append(step)

        if any_replaced:
            new_plan = copy.copy(plan)
            new_plan.steps = new_steps
            return RecoveryResult(
                recovered=True,
                action="retry_agent",
                reason=f"Replaced agents for steps: {list(replaced.keys())}",
                new_plan=new_plan,
                replaced_agents=replaced,
            )

        return RecoveryResult(
            recovered=False,
            action="abort",
            reason="No alternative agents available",
        )