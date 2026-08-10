"""
LLMPlanner 测试
覆盖：Mock provider 正常解析、fallback 到规则引擎、JSON 清理。
"""

import json
import pytest

from app.orchestrator.llm_planner import LLMPlanner
from app.orchestrator.planner import TaskPlanner, TaskPlan, TaskType
from app.orchestrator.llm_provider import (
    LLMProvider, LLMMessage, LLMResponse, LLMTool,
)


# === 测试用可控 Provider ===

class FakeLLMProvider(LLMProvider):
    """可控返回内容的 Provider，用于测试 JSON 解析"""

    def __init__(self, response_content: str):
        self._content = response_content

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        return LLMResponse(content=self._content, model="fake", tokens_used=10)

    def get_model_name(self) -> str:
        return "fake"

    def is_available(self) -> bool:
        return True


class FailingLLMProvider(LLMProvider):
    """始终抛异常的 Provider，用于测试 fallback"""

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=4096, tools=None, **kwargs):
        raise RuntimeError("API connection failed")

    def get_model_name(self) -> str:
        return "failing"

    def is_available(self) -> bool:
        return False


# === 测试 JSON 响应 ===

GOOD_JSON = json.dumps({
    "steps": [
        {"id": "research", "type": "research", "description": "采集AI新闻", "depends_on": [], "agent_hint": "research"},
        {"id": "analysis", "type": "analysis", "description": "分析价值", "depends_on": ["research"], "agent_hint": "analysis"},
        {"id": "writing", "type": "writing", "description": "生成文章", "depends_on": ["analysis"], "agent_hint": "writing"},
    ],
    "context_query": "AI 新闻",
})

GOOD_JSON_IN_CODEBLOCK = "```json\n" + GOOD_JSON + "\n```"

GOOD_JSON_WITH_EXTRA = "好的，我来拆解任务：\n" + GOOD_JSON + "\n以上是拆解结果。"

BAD_JSON = "这不是一个有效的JSON"

EMPTY_STEPS_JSON = json.dumps({"steps": [], "context_query": ""})


class TestLLMPlannerNormal:

    @pytest.mark.asyncio
    async def test_basic_plan(self):
        provider = FakeLLMProvider(GOOD_JSON)
        planner = LLMPlanner(provider)
        plan = await planner.plan("写一篇AI新闻")

        assert isinstance(plan, TaskPlan)
        assert plan.intent == "写一篇AI新闻"
        assert len(plan.steps) == 3
        assert plan.steps[0].type == TaskType.RESEARCH
        assert plan.steps[1].depends_on == ["research"]
        assert plan.context_query == "AI 新闻"

    @pytest.mark.asyncio
    async def test_json_in_codeblock(self):
        provider = FakeLLMProvider(GOOD_JSON_IN_CODEBLOCK)
        planner = LLMPlanner(provider)
        plan = await planner.plan("写一篇AI新闻")
        assert len(plan.steps) == 3

    @pytest.mark.asyncio
    async def test_json_with_extra_text(self):
        provider = FakeLLMProvider(GOOD_JSON_WITH_EXTRA)
        planner = LLMPlanner(provider)
        plan = await planner.plan("写一篇AI新闻")
        assert len(plan.steps) == 3

    @pytest.mark.asyncio
    async def test_context_query_preserved(self):
        provider = FakeLLMProvider(GOOD_JSON)
        planner = LLMPlanner(provider)
        plan = await planner.plan("写一篇AI新闻")
        assert plan.context_query == "AI 新闻"


class TestLLMPlannerFallback:

    @pytest.mark.asyncio
    async def test_api_failure_fallback(self):
        provider = FailingLLMProvider()
        planner = LLMPlanner(provider)
        plan = await planner.plan("写一篇AI新闻")

        # fallback 到规则引擎，应返回 content pipeline (5 步)
        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) == 5
        assert plan.steps[0].type == TaskType.RESEARCH

    @pytest.mark.asyncio
    async def test_bad_json_fallback(self):
        provider = FakeLLMProvider(BAD_JSON)
        planner = LLMPlanner(provider)
        plan = await planner.plan("写一篇AI新闻")

        # JSON 解析失败，fallback
        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) == 5

    @pytest.mark.asyncio
    async def test_empty_steps_fallback(self):
        provider = FakeLLMProvider(EMPTY_STEPS_JSON)
        planner = LLMPlanner(provider)
        plan = await planner.plan("写一篇AI新闻")

        # steps 为空，fallback
        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) == 5

    @pytest.mark.asyncio
    async def test_fallback_chat_intent(self):
        provider = FailingLLMProvider()
        planner = LLMPlanner(provider)
        plan = await planner.plan("你好")

        # 简单对话 fallback
        assert isinstance(plan, TaskPlan)
        assert plan.steps[0].type == TaskType.CHAT


class TestLLMPlannerEdgeCases:

    @pytest.mark.asyncio
    async def test_unknown_type_becomes_custom(self):
        data = {
            "steps": [{"id": "s1", "type": "unknown_type", "description": "test"}],
            "context_query": "",
        }
        provider = FakeLLMProvider(json.dumps(data))
        planner = LLMPlanner(provider)
        plan = await planner.plan("test")
        assert plan.steps[0].type == TaskType.CUSTOM

    def test_clean_json_with_codeblock(self):
        raw = "```json\n{\"key\": 1}\n```"
        assert LLMPlanner._clean_json(raw) == '{"key": 1}'

    def test_clean_json_with_extra(self):
        raw = "说明文字\n{\"key\": 1}\n结束"
        assert LLMPlanner._clean_json(raw) == '{"key": 1}'