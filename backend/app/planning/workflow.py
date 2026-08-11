"""
WorkflowGenerator — 规则型工作流生成器。

根据用户输入的任务描述，通过关键词匹配识别所需能力，
生成带 DAG 依赖的 TaskPlan。

不依赖 LLM，纯规则引擎实现。
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry

logger = get_logger(__name__)

# 能力 -> 关键词映射
CAPABILITY_KEYWORDS: dict[str, list[str]] = {
    "research": ["研究", "搜索", "调研", "分析资料", "搜集", "查找", "采集", "了解"],
    "analysis": ["分析", "评估", "比较", "判断", "评测", "对比"],
    "writing": ["写", "报告", "文章", "总结文档", "撰写", "编写", "创作", "草稿"],
    "image": ["图片", "封面", "配图", "海报", "设计"],
    "seo": ["标题", "标签", "话题", "关键词", "优化"],
}

# 能力 -> TaskType 映射
CAPABILITY_TASK_TYPE: dict[str, TaskType] = {
    "research": TaskType.RESEARCH,
    "analysis": TaskType.ANALYSIS,
    "writing": TaskType.WRITING,
    "image": TaskType.IMAGE,
    "seo": TaskType.SEO,
}

# 能力之间的默认依赖顺序
# 排在前面的能力是后面能力的前置依赖
CAPABILITY_ORDER: list[str] = ["research", "analysis", "writing", "image", "seo"]


@dataclass
class MatchedCapability:
    """匹配到的能力"""
    capability: str
    task_type: TaskType
    agent_id: str | None


class WorkflowGenerator:
    """
    规则型工作流生成器。

    流程：
    1. 从任务描述中提取关键词
    2. 匹配所需能力 (capability)
    3. 通过 AgentRegistry 查找具备该能力的 Agent
    4. 按能力依赖顺序生成 TaskPlan (DAG)

    用法：
        generator = WorkflowGenerator(agent_registry)
        plan = generator.generate("研究AI趋势并写报告")
    """

    def __init__(self, agent_registry: "AgentRegistry | None" = None):
        self._registry = agent_registry

    def generate(self, task: str) -> TaskPlan:
        """
        根据任务描述生成 TaskPlan。
        Args:
            task: 用户任务描述
        Returns:
            TaskPlan（带 DAG 依赖）
        Raises:
            ValueError: 任务为空或无法识别任何能力
        """
        if not task or not task.strip():
            raise ValueError("Task description cannot be empty")

        task = task.strip()

        # Step 1: 识别所需能力
        matched = self._match_capabilities(task)
        if not matched:
            # 无法识别能力时，生成一个 CHAT 类型的兜底步骤
            logger.warning("No capability matched, generating fallback step", task=task[:50])
            return TaskPlan(
                intent=task,
                steps=[TaskStep(
                    id="chat",
                    type=TaskType.CHAT,
                    description=task,
                    agent_hint="default",
                )],
                context_query=task[:50],
            )

        # Step 2: 按能力顺序排序
        matched = self._sort_by_order(matched)

        # Step 3: 生成 TaskStep 列表（带依赖）
        steps = self._build_steps(matched, task)

        logger.info(
            "Workflow generated",
            task=task[:50],
            capabilities=[m.capability for m in matched],
            steps=len(steps),
        )

        return TaskPlan(
            intent=task,
            steps=steps,
            context_query=task[:50],
        )

    def _match_capabilities(self, task: str) -> list[MatchedCapability]:
        """从任务描述中匹配所需能力"""
        matched = []
        seen = set()

        for capability, keywords in CAPABILITY_KEYWORDS.items():
            for kw in keywords:
                if kw in task and capability not in seen:
                    seen.add(capability)
                    task_type = CAPABILITY_TASK_TYPE.get(capability, TaskType.CUSTOM)
                    agent_id = self._find_agent(capability)
                    matched.append(MatchedCapability(
                        capability=capability,
                        task_type=task_type,
                        agent_id=agent_id,
                    ))
                    break  # 每个能力只匹配一次

        return matched

    def _find_agent(self, capability: str) -> str | None:
        """通过 AgentRegistry 查找具备指定能力的 Agent"""
        if not self._registry:
            return None
        agents = self._registry.get_agents_by_capability(capability)
        return agents[0] if agents else None

    @staticmethod
    def _sort_by_order(matched: list[MatchedCapability]) -> list[MatchedCapability]:
        """按能力依赖顺序排序"""
        order_map = {cap: i for i, cap in enumerate(CAPABILITY_ORDER)}
        return sorted(matched, key=lambda m: order_map.get(m.capability, 999))

    @staticmethod
    def _build_steps(matched: list[MatchedCapability], task: str) -> list[TaskStep]:
        """生成 TaskStep 列表，自动设置 DAG 依赖"""
        steps = []
        prev_id = None

        for m in matched:
            step_id = m.capability
            depends_on = [prev_id] if prev_id else []

            step = TaskStep(
                id=step_id,
                type=m.task_type,
                description=f"{m.capability}: {task}",
                depends_on=depends_on,
                agent_hint=m.agent_id or "",
                params={"user_input": task, "capability": m.capability},
            )
            steps.append(step)
            prev_id = step_id

        return steps