"""LLM-driven task planner with rule-based fallback (Phase Beta-LLM)."""

from __future__ import annotations

import json
from typing import Any

from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.planning.workflow import WorkflowGenerator
from app.llm.models import LLMMessage, LLMRole
from app.llm.provider import LLMProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a task planner. Convert the user request into a JSON plan. "
    "Return only JSON in this shape: "
    '{"intent": "string", "context_query": "string", "steps": ['
    '{"id": "string", "type": "research|analysis|writing|image|seo|chat|custom", '
    '"description": "string", "depends_on": ["step_id"], "agent_hint": "string"}]}. '
    "Do not include markdown or extra text."
)


class LLMPlanner:
    """Plan tasks with an LLM, falling back to WorkflowGenerator on any failure."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        fallback_generator: WorkflowGenerator | None = None,
    ) -> None:
        self._llm = llm_provider
        self._fallback = fallback_generator or WorkflowGenerator()

    async def plan(self, task: str) -> TaskPlan:
        if not task or not task.strip():
            raise ValueError("Task description cannot be empty")

        if self._llm is None:
            return self._fallback.generate(task)

        try:
            return await self._plan_with_llm(task.strip())
        except Exception as exc:  # noqa: BLE001 - fallback by design
            logger.warning("LLM planning failed, falling back to WorkflowGenerator", error=str(exc))
            return self._fallback.generate(task)

    async def _plan_with_llm(self, task: str) -> TaskPlan:
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content=SYSTEM_PROMPT),
            LLMMessage(role=LLMRole.USER, content=task),
        ]
        response = await self._llm.generate(messages, temperature=0.2, max_tokens=2048)
        data = self._parse_response(response.content)
        return self._build_task_plan(data, task)

    @staticmethod
    def _parse_response(content: str) -> dict[str, Any]:
        text = (content or "").strip()
        text = LLMPlanner._strip_code_block(text)
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM response did not contain a JSON object")
        data = json.loads(text[start:end + 1])
        if not isinstance(data, dict):
            raise ValueError("LLM response JSON must be an object")
        return data

    @staticmethod
    def _strip_code_block(text: str) -> str:
        if text.startswith("```"):
            first_newline = text.find("\n")
            if first_newline != -1:
                text = text[first_newline + 1:]
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3].rstrip()
        return text

    def _build_task_plan(self, data: dict[str, Any], task: str) -> TaskPlan:
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ValueError("LLM response steps is empty or invalid")

        steps: list[TaskStep] = []
        for index, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                continue
            step_id = str(item.get("id") or "step_" + str(index + 1))
            raw_type = str(item.get("type") or "custom")
            try:
                step_type = TaskType(raw_type)
            except ValueError:
                logger.warning("Unknown task type from LLM, using custom", type=raw_type)
                step_type = TaskType.CUSTOM
            depends_on = item.get("depends_on") or []
            if not isinstance(depends_on, list):
                depends_on = [str(depends_on)]
            steps.append(TaskStep(
                id=step_id,
                type=step_type,
                description=str(item.get("description") or task),
                depends_on=[str(dep) for dep in depends_on],
                agent_hint=str(item.get("agent_hint") or ""),
                params={"user_input": task},
            ))

        if not steps:
            raise ValueError("No valid steps parsed from LLM response")

        return TaskPlan(
            intent=str(data.get("intent") or task),
            steps=steps,
            context_query=str(data.get("context_query") or task[:50]),
        )


def create_llm_planner(llm_provider: LLMProvider | None = None) -> LLMPlanner:
    """Create an LLMPlanner using the configured provider when available."""
    if llm_provider is None:
        from app.llm.factory import get_llm_provider
        llm_provider = get_llm_provider()
    return LLMPlanner(llm_provider=llm_provider)
