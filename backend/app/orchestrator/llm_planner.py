"""
LLM 驱动的任务规划器
使用 LLM 将用户意图拆解为结构化 TaskPlan。
失败时自动 fallback 到规则引擎 TaskPlanner。
"""

import json

from app.orchestrator.planner import TaskPlanner, TaskPlan, TaskStep, TaskType
from app.orchestrator.llm_provider import LLMProvider, LLMMessage, LLMRole
from app.utils.logger import get_logger

logger = get_logger(__name__)

# TaskType 枚举值白名单，用于校验 LLM 输出
_VALID_TYPES = {t.value for t in TaskType}

SYSTEM_PROMPT = """你是一个任务规划器。用户会给你一个任务描述，你需要把它拆解成若干可执行步骤。

必须返回严格的 JSON 格式（不要包含 markdown 代码块标记），结构如下：
{
  "steps": [
    {
      "id": "step_1",
      "type": "research",
      "description": "步骤描述",
      "depends_on": [],
      "agent_hint": "research"
    }
  ],
  "context_query": "用于知识库检索的关键词"
}

type 可选值: research, analysis, writing, image, seo, chat, custom
depends_on 填写依赖的步骤 id 列表。
agent_hint 可选: research, analysis, writing, image, seo, default
context_query: 从用户输入中提取的核心主题关键词，用于检索知识库。

规则：
1. 如果是简单对话（你好/请问等），只返回一个 chat 类型步骤。
2. 如果是内容生产任务，通常包含 research -> analysis -> writing -> image -> seo 流程。
3. steps 至少有 1 个，最多不超过 8 个。
4. 只返回 JSON，不要有其他文字。"""


class LLMPlanner:
    """
    LLM 驱动的任务规划器
    使用 LLM 将用户意图拆解为 TaskPlan。
    解析失败时 fallback 到规则引擎 TaskPlanner。
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self._fallback = TaskPlanner()

    async def plan(self, user_input: str) -> TaskPlan:
        """
        使用 LLM 生成任务计划
        Args:
            user_input: 用户任务描述
        Returns:
            TaskPlan
        """
        try:
            response = await self.llm.chat(
                messages=[
                    LLMMessage(role=LLMRole.SYSTEM, content=SYSTEM_PROMPT),
                    LLMMessage(role=LLMRole.USER, content=user_input),
                ],
                temperature=0.3,
                max_tokens=2048,
            )
            return self._parse_response(user_input, response.content)
        except Exception as e:  # noqa: BLE001 — fallback to rule planner
            logger.warning("LLM planner failed, falling back to rule planner", error=str(e))
            return self._fallback.plan(user_input)

    def _parse_response(self, user_input: str, raw: str) -> TaskPlan:
        """解析 LLM 返回的 JSON 为 TaskPlan"""
        cleaned = self._clean_json(raw)
        data = json.loads(cleaned)

        raw_steps = data.get("steps", [])
        if not raw_steps or not isinstance(raw_steps, list):
            raise ValueError("steps is empty or not a list")

        steps: list[TaskStep] = []
        for item in raw_steps:
            step_type = item.get("type", "custom")
            if step_type not in _VALID_TYPES:
                logger.warning("Unknown step type from LLM, using custom", type=step_type)
                step_type = "custom"

            steps.append(TaskStep(
                id=item.get("id", f"step_{len(steps) + 1}"),
                type=TaskType(step_type),
                description=item.get("description", ""),
                depends_on=item.get("depends_on", []),
                agent_hint=item.get("agent_hint", ""),
                params={"user_input": user_input},
            ))

        context_query = data.get("context_query", "")

        return TaskPlan(
            intent=user_input,
            steps=steps,
            context_query=context_query,
        )

    @staticmethod
    def _clean_json(raw: str) -> str:
        """
        清理 LLM 输出中的 markdown 代码块标记等杂质。
        支持: ```json ... ```, ``` ... ```, 前后多余文字。
        """
        text = raw.strip()
        # 去除 ```json ... ``` 包裹
        if text.startswith("```"):
            # 找到第一个换行后的内容
            first_nl = text.find("\n")
            if first_nl != -1:
                text = text[first_nl + 1:]
            # 去除尾部 ```
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3].rstrip()
        # 尝试找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]
        return text