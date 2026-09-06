"""Tests for the Phase Beta-LLM planner integration."""

import json

import pytest

from app.llm.models import LLMResponse
from app.llm.planner import LLMPlanner
from app.orchestrator.planner import TaskPlan, TaskType


class FakeProvider:
    def __init__(self, content):
        self.content = content
        self.calls = []

    async def generate(self, messages, model=None, temperature=0.2, max_tokens=4000, **kwargs):
        self.calls.append({"messages": messages, "model": model})
        return LLMResponse(content=self.content, model="fake")


class FailingProvider:
    async def generate(self, messages, model=None, temperature=0.2, max_tokens=4000, **kwargs):
        raise RuntimeError("llm down")


GOOD_PLAN = json.dumps({
    "intent": "research task",
    "context_query": "AI trends",
    "steps": [
        {"id": "research", "type": "research", "description": "search", "depends_on": [], "agent_hint": "researcher"},
        {"id": "write", "type": "writing", "description": "write", "depends_on": ["research"], "agent_hint": "writer"},
    ],
})

BT = chr(96)


class TestLLMPlannerNormal:
    @pytest.mark.asyncio
    async def test_plan_returns_task_plan(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        plan = await planner.plan("research task")
        assert isinstance(plan, TaskPlan)

    @pytest.mark.asyncio
    async def test_plan_has_steps(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        plan = await planner.plan("research task")
        assert len(plan.steps) == 2

    @pytest.mark.asyncio
    async def test_plan_preserves_intent(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        plan = await planner.plan("research task")
        assert plan.intent == "research task"

    @pytest.mark.asyncio
    async def test_plan_preserves_context_query(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        plan = await planner.plan("research task")
        assert plan.context_query == "AI trends"

    @pytest.mark.asyncio
    async def test_plan_maps_step_type(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        plan = await planner.plan("research task")
        assert plan.steps[0].type == TaskType.RESEARCH
        assert plan.steps[1].type == TaskType.WRITING

    @pytest.mark.asyncio
    async def test_plan_preserves_dependencies(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        plan = await planner.plan("research task")
        assert plan.steps[1].depends_on == ["research"]

    @pytest.mark.asyncio
    async def test_plan_preserves_agent_hint(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        plan = await planner.plan("research task")
        assert plan.steps[0].agent_hint == "researcher"


class TestLLMPlannerParsing:
    @pytest.mark.asyncio
    async def test_markdown_code_block(self):
        planner = LLMPlanner(FakeProvider(BT * 3 + "json" + chr(10) + GOOD_PLAN + chr(10) + BT * 3))
        plan = await planner.plan("research task")
        assert len(plan.steps) == 2

    @pytest.mark.asyncio
    async def test_extra_text_around_json(self):
        planner = LLMPlanner(FakeProvider("Here is the plan:" + chr(10) + GOOD_PLAN + chr(10) + "Done."))
        plan = await planner.plan("research task")
        assert len(plan.steps) == 2

    def test_parse_response_returns_dict(self):
        data = LLMPlanner._parse_response(GOOD_PLAN)
        assert data["intent"] == "research task"

    def test_strip_code_block(self):
        text = LLMPlanner._strip_code_block(BT * 3 + "json" + chr(10) + "{}" + chr(10) + BT * 3)
        assert "{}" in text

    def test_parse_response_invalid_json_raises(self):
        with pytest.raises(ValueError):
            LLMPlanner._parse_response("not json")


class TestLLMPlannerFallback:
    @pytest.mark.asyncio
    async def test_llm_failure_falls_back(self):
        planner = LLMPlanner(FailingProvider())
        plan = await planner.plan("research task")
        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) >= 1

    @pytest.mark.asyncio
    async def test_invalid_json_falls_back(self):
        planner = LLMPlanner(FakeProvider("not json"))
        plan = await planner.plan("write a report")
        assert isinstance(plan, TaskPlan)
        assert plan.steps[0].type == TaskType.WRITING

    @pytest.mark.asyncio
    async def test_empty_steps_falls_back(self):
        planner = LLMPlanner(FakeProvider(json.dumps({"steps": []})))
        plan = await planner.plan("write a report")
        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) >= 1

    @pytest.mark.asyncio
    async def test_none_provider_falls_back(self):
        planner = LLMPlanner(None)
        plan = await planner.plan("write a report")
        assert isinstance(plan, TaskPlan)

    @pytest.mark.asyncio
    async def test_unknown_type_becomes_custom(self):
        content = json.dumps({"steps": [{"id": "x", "type": "unknown", "description": "d"}]})
        planner = LLMPlanner(FakeProvider(content))
        plan = await planner.plan("anything")
        assert plan.steps[0].type == TaskType.CUSTOM

    @pytest.mark.asyncio
    async def test_depends_on_string_is_coerced(self):
        content = json.dumps({"steps": [{"id": "x", "type": "research", "depends_on": "y"}]})
        planner = LLMPlanner(FakeProvider(content))
        plan = await planner.plan("anything")
        assert plan.steps[0].depends_on == ["y"]

    @pytest.mark.asyncio
    async def test_missing_ids_are_generated(self):
        content = json.dumps({"steps": [{"type": "research", "description": "d"}]})
        planner = LLMPlanner(FakeProvider(content))
        plan = await planner.plan("anything")
        assert plan.steps[0].id == "step_1"


class TestLLMPlannerValidation:
    @pytest.mark.asyncio
    async def test_empty_task_raises(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        with pytest.raises(ValueError):
            await planner.plan("")

    @pytest.mark.asyncio
    async def test_whitespace_task_raises(self):
        planner = LLMPlanner(FakeProvider(GOOD_PLAN))
        with pytest.raises(ValueError):
            await planner.plan("   ")


class TestLLMPlannerMore:
    def test_strip_code_block_plain_text_unchanged(self):
        assert LLMPlanner._strip_code_block("hello") == "hello"

    def test_parse_response_no_json_raises(self):
        with pytest.raises(ValueError):
            LLMPlanner._parse_response("plain text")

    @pytest.mark.asyncio
    async def test_seo_step_type_is_preserved(self):
        content = json.dumps({"steps": [{"id": "seo", "type": "seo", "description": "titles"}]})
        plan = await LLMPlanner(FakeProvider(content)).plan("anything")
        assert plan.steps[0].type == TaskType.SEO

    @pytest.mark.asyncio
    async def test_depends_on_none_becomes_empty(self):
        content = json.dumps({"steps": [{"id": "x", "type": "research", "depends_on": None}]})
        plan = await LLMPlanner(FakeProvider(content)).plan("anything")
        assert plan.steps[0].depends_on == []

