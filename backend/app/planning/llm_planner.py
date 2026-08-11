"""
LLMPlanner — LLM 驱动的任务规划器。

通过 LLM 将用户任务描述转化为结构化 TaskPlan。
LLM 返回 JSON 格式的步骤和依赖关系，
解析后生成 TaskPlan。

失败时自动 fallback 到规则型 WorkflowGenerator。
"""

import json
from typing import TYPE_CHECKING

from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.agents.selector import AgentSelector
from app.planning.workflow import WorkflowGenerator, CAPABILITY_TASK_TYPE
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.registry import AgentRegistry
    from app.orchestrator.llm_provider import LLMProvider

logger = get_logger(__name__)

# LLM 规划 Prompt 模板
PLANNING_PROMPT = """你是一个任务规划器。根据用户的任务描述，将其分解为执行步骤。

请返回 JSON 格式（不要包含其他内容）：
{
  "steps": [
    {
      "id": "research",
      "capability": "research",
      "description": "采集相关信息"
    }
  ],
  "dependencies": [
    {"from": "research", "to": "analysis"}
  ]
}

有效的 capability 值：research, analysis, writing, image, seo

用户任务：{task}"""

# capability -> TaskType 映射（与 WorkflowGenerator 一致）
_CAPABILITY_TO_TYPE: dict[str, TaskType] = {
    "research": TaskType.RESEARCH,
    "analysis": TaskType.ANALYSIS,
    "writing": TaskType.WRITING,
    "image": TaskType.IMAGE,
    "seo": TaskType.SEO,
}


class LLMPlanner:
    """
    LLM 驱动的任务规划器。

    流程：
    1. 将用户任务发送给 LLM
    2. 解析 LLM 返回的 JSON 步骤
    3. 通过 CapabilityRegistry 查找 Agent
    4. 生成 TaskPlan（带 DAG 依赖）

    失败时 fallback 到 WorkflowGenerator（规则型）。

    用法：
        planner = LLMPlanner(llm_provider, agent_registry)
        plan = await planner.plan("研究AI趋势并写报告")
    """

    def __init__(
        self,
        llm_provider: "LLMProvider",
        agent_registry: "AgentRegistry | None" = None,
        fallback_planner: WorkflowGenerator | None = None,
    ):
        self._llm = llm_provider
        self._registry = agent_registry
        self._selector = AgentSelector(agent_registry) if agent_registry else None
        self._fallback = fallback_planner or WorkflowGenerator(agent_registry)

    async def plan(self, task: str) -> TaskPlan:
        """
        使用 LLM 生成任务计划。
        失败时 fallback 到规则型 WorkflowGenerator。
        Args:
            task: 用户任务描述
        Returns:
            TaskPlan
        """
        if not task or not task.strip():
            raise ValueError("Task description cannot be empty")

        task = task.strip()

        try:
            return await self._plan_with_llm(task)
        except Exception as e:  # noqa: BLE001 fallback on any LLM failure
            logger.warning("LLM planning failed, falling back to WorkflowGenerator", error=str(e))
            return self._fallback.generate(task)

    async def _plan_with_llm(self, task: str) -> TaskPlan:
        """调用 LLM 生成计划"""
        from app.orchestrator.llm_provider import LLMMessage, LLMRole

        prompt = PLANNING_PROMPT.format(task=task)
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content="你是任务规划器，只输出JSON。"),
            LLMMessage(role=LLMRole.USER, content=prompt),
        ]

        response = await self._llm.chat(messages=messages, temperature=0.3)
        plan_data = self._parse_response(response.content)
        return self._build_task_plan(plan_data, task)

    @staticmethod
    def _parse_response(content: str) -> dict:
        """解析 LLM 返回的 JSON"""
        # 尝试提取 JSON（可能被 markdown 包裹）
        text = content.strip()
        if text.startswith("```"):
            # 去掉 markdown 代码块
            lines = text.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    json_lines.append(line)
            text = "\n".join(json_lines)

        return json.loads(text)

    def _build_task_plan(self, plan_data: dict, original_task: str) -> TaskPlan:
        """将解析后的 JSON 转换为 TaskPlan"""
        raw_steps = plan_data.get("steps", [])
        raw_deps = plan_data.get("dependencies", [])

        if not raw_steps:
            raise ValueError("LLM returned empty steps")

        # 构建依赖映射: step_id -> [dep_ids]
        dep_map: dict[str, list[str]] = {}
        for dep in raw_deps:
            from_id = dep.get("from", "")
            to_id = dep.get("to", "")
            if from_id and to_id:
                if to_id not in dep_map:
                    dep_map[to_id] = []
                dep_map[to_id].append(from_id)

        steps = []
        for raw in raw_steps:
            step_id = raw.get("id", "")
            capability = raw.get("capability", "")
            description = raw.get("description", original_task)

            if not step_id:
                continue

            task_type = _CAPABILITY_TO_TYPE.get(capability, TaskType.CUSTOM)
            agent_id = self._find_agent(capability)
            depends_on = dep_map.get(step_id, [])

            steps.append(TaskStep(
                id=step_id,
                type=task_type,
                description=description,
                depends_on=depends_on,
                agent_hint=agent_id or "",
                params={"user_input": original_task, "capability": capability},
            ))

        if not steps:
            raise ValueError("No valid steps parsed from LLM response")

        return TaskPlan(
            intent=original_task,
            steps=steps,
            context_query=original_task[:50],
        )

    def _find_agent(self, capability: str) -> str | None:
        """通过 AgentSelector 查找最佳 Agent"""
        if not self._selector or not capability:
            return None
        return self._selector.select(capability)