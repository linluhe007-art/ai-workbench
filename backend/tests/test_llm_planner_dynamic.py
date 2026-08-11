"""
Phase 3.11.1 测试 — LLMPlanner
覆盖：
- Mock LLM 正常 JSON → TaskPlan
- capability 匹配 Agent
- 无 Agent fallback
- LLM 异常 fallback 到 WorkflowGenerator
- 多步骤 DAG 依赖
- 空任务异常
"""

import json
import pytest

from app.planning.llm_planner import LLMPlanner
from app.orchestrator.planner import TaskPlan, TaskType
from app.orchestrator.llm_provider import (
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMRole,
)
from app.agents.registry import AgentRegistry
from app.agents.mock_agent import MockAgent
from app.agents.base import AgentType


# ─── Test Helpers ───────────────────────────────────────────


class FakePlanningLLM(LLMProvider):
    """返回预设 JSON 计划的 Mock LLM"""

    def __init__(self, plan_json: dict):
        self._plan = plan_json
        self._call_count = 0

    async def chat(self, messages, model=None, temperature=0.7,
                   max_tokens=4096, tools=None, **kwargs) -> LLMResponse:
        self._call_count += 1
        return LLMResponse(
            content=json.dumps(self._plan, ensure_ascii=False),
            model="fake-planner-v1",
            tokens_used=100,
            finish_reason="stop",
        )


class FailingLLM(LLMProvider):
    """总是抛异常的 Mock LLM"""

    async def chat(self, messages, model=None, temperature=0.7,
                   max_tokens=4096, tools=None, **kwargs) -> LLMResponse:
        raise RuntimeError("LLM service unavailable")


# ─── Tests ─────────────────────────────────────────────────


class TestLLMPlannerNormal:

    @pytest.mark.asyncio
    async def test_single_step(self):
        llm = FakePlanningLLM({
            "steps": [
                {"id": "research", "capability": "research", "description": "采集AI新闻"}
            ],
            "dependencies": [],
        })
        planner = LLMPlanner(llm)
        plan = await planner.plan("搜索资料")

        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) == 1
        assert plan.steps[0].id == "research"
        assert plan.steps[0].type == TaskType.RESEARCH
        assert plan.steps[0].description == "采集AI新闻"

    @pytest.mark.asyncio
    async def test_multi_step_with_deps(self):
        llm = FakePlanningLLM({
            "steps": [
                {"id": "research", "capability": "research", "description": "搜索"},
                {"id": "analysis", "capability": "analysis", "description": "分析"},
                {"id": "writing", "capability": "writing", "description": "写报告"},
            ],
            "dependencies": [
                {"from": "research", "to": "analysis"},
                {"from": "analysis", "to": "writing"},
            ],
        })
        planner = LLMPlanner(llm)
        plan = await planner.plan("研究并写报告")

        assert len(plan.steps) == 3
        assert plan.steps[1].depends_on == ["research"]
        assert plan.steps[2].depends_on == ["analysis"]

    @pytest.mark.asyncio
    async def test_parallel_steps(self):
        llm = FakePlanningLLM({
            "steps": [
                {"id": "research", "capability": "research", "description": "搜索"},
                {"id": "writing", "capability": "writing", "description": "写"},
                {"id": "image", "capability": "image", "description": "封面"},
            ],
            "dependencies": [
                {"from": "research", "to": "writing"},
                {"from": "research", "to": "image"},
            ],
        })
        planner = LLMPlanner(llm)
        plan = await planner.plan("研究后写文章和做封面")

        assert len(plan.steps) == 3
        assert plan.steps[1].depends_on == ["research"]
        assert plan.steps[2].depends_on == ["research"]

    @pytest.mark.asyncio
    async def test_intent_preserved(self):
        llm = FakePlanningLLM({
            "steps": [{"id": "research", "capability": "research", "description": "d"}],
            "dependencies": [],
        })
        planner = LLMPlanner(llm)
        plan = await planner.plan("研究AI趋势")

        assert plan.intent == "研究AI趋势"


class TestLLMPlannerAgentSelection:

    @pytest.mark.asyncio
    async def test_capability_matches_agent(self):
        reg = AgentRegistry()
        reg.clear()
        agent = MockAgent("researcher")
        agent.config.capabilities = ["research"]
        reg.register(agent)

        llm = FakePlanningLLM({
            "steps": [{"id": "research", "capability": "research", "description": "d"}],
            "dependencies": [],
        })
        planner = LLMPlanner(llm, agent_registry=reg)
        plan = await planner.plan("搜索资料")

        assert plan.steps[0].agent_hint == "researcher"

    @pytest.mark.asyncio
    async def test_no_matching_agent_hint_empty(self):
        reg = AgentRegistry()
        reg.clear()

        llm = FakePlanningLLM({
            "steps": [{"id": "research", "capability": "research", "description": "d"}],
            "dependencies": [],
        })
        planner = LLMPlanner(llm, agent_registry=reg)
        plan = await planner.plan("搜索资料")

        assert plan.steps[0].agent_hint == ""

    @pytest.mark.asyncio
    async def test_no_registry(self):
        llm = FakePlanningLLM({
            "steps": [{"id": "research", "capability": "research", "description": "d"}],
            "dependencies": [],
        })
        planner = LLMPlanner(llm, agent_registry=None)
        plan = await planner.plan("搜索资料")

        assert plan.steps[0].agent_hint == ""


class TestLLMPlannerFallback:

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back(self):
        failing = FailingLLM()
        planner = LLMPlanner(failing)
        plan = await planner.plan("搜索资料")

        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) >= 1
        assert plan.steps[0].type == TaskType.RESEARCH

    @pytest.mark.asyncio
    async def test_llm_invalid_json_falls_back(self):
        class BadJSONLLM(LLMProvider):
            async def chat(self, messages, **kwargs) -> LLMResponse:
                return LLMResponse(content="not json", model="bad")

        planner = LLMPlanner(BadJSONLLM())
        plan = await planner.plan("写报告")

        assert isinstance(plan, TaskPlan)
        assert plan.steps[0].type == TaskType.WRITING

    @pytest.mark.asyncio
    async def test_llm_empty_steps_falls_back(self):
        llm = FakePlanningLLM({"steps": [], "dependencies": []})
        planner = LLMPlanner(llm)
        plan = await planner.plan("写报告")

        assert isinstance(plan, TaskPlan)
        assert len(plan.steps) >= 1


class TestLLMPlannerEdgeCases:

    @pytest.mark.asyncio
    async def test_empty_task_raises(self):
        llm = FakePlanningLLM({"steps": [], "dependencies": []})
        planner = LLMPlanner(llm)
        with pytest.raises(ValueError, match="empty"):
            await planner.plan("")

    @pytest.mark.asyncio
    async def test_markdown_wrapped_json(self):
        class MarkdownLLM(LLMProvider):
            async def chat(self, messages, **kwargs) -> LLMResponse:
                json_str = json.dumps({
                    "steps": [{"id": "research", "capability": "research", "description": "d"}],
                    "dependencies": [],
                })
                return LLMResponse(content=f"```json\n{json_str}\n```", model="md")

        planner = LLMPlanner(MarkdownLLM())
        plan = await planner.plan("搜索资料")

        assert len(plan.steps) == 1
        assert plan.steps[0].type == TaskType.RESEARCH

class TestLLMPlannerUsesSelector:
    """验证 LLMPlanner 通过 AgentSelector 选择 Agent"""

    @pytest.mark.asyncio
    async def test_selector_picks_best_agent(self):
        """AgentSelector 应选择 capability 更多的 Agent"""
        reg = AgentRegistry()
        reg.clear()
        basic = MockAgent("basic")
        basic.config.capabilities = ["research"]
        advanced = MockAgent("advanced")
        advanced.config.capabilities = ["research", "analysis", "writing"]
        reg.register(basic)
        reg.register(advanced)

        llm = FakePlanningLLM({
            "steps": [{"id": "research", "capability": "research", "description": "d"}],
            "dependencies": [],
        })
        planner = LLMPlanner(llm, agent_registry=reg)
        plan = await planner.plan("搜索资料")

        assert plan.steps[0].agent_hint == "advanced"

    @pytest.mark.asyncio
    async def test_selector_respects_score(self):
        """AgentSelector 应优先选择 score 更高的 Agent"""
        reg = AgentRegistry()
        reg.clear()
        a1 = MockAgent("low-score")
        a1.config.capabilities = ["research"]
        a1.config.extra["score"] = 1
        a2 = MockAgent("high-score")
        a2.config.capabilities = ["research"]
        a2.config.extra["score"] = 10
        reg.register(a1)
        reg.register(a2)

        llm = FakePlanningLLM({
            "steps": [{"id": "research", "capability": "research", "description": "d"}],
            "dependencies": [],
        })
        planner = LLMPlanner(llm, agent_registry=reg)
        plan = await planner.plan("搜索资料")

        assert plan.steps[0].agent_hint == "high-score"