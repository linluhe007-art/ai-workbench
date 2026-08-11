"""
Phase 3.16 测试 — RePlanner
"""

import pytest
from app.planning.replanner import RePlanner
from app.execution.feedback import FeedbackResult
from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.agents.registry import AgentRegistry
from app.agents.mock_agent import MockAgent
from app.agents.selector import AgentSelector


def _make_plan(steps: list[tuple]) -> TaskPlan:
    task_steps = []
    for item in steps:
        sid, stype, hint = item[0], item[1], item[2] if len(item) > 2 else ""
        task_steps.append(TaskStep(
            id=sid, type=stype, description=f"desc-{sid}",
            agent_hint=hint, params={"capability": stype.value},
        ))
    return TaskPlan(intent="test", steps=task_steps)


def _make_selector(agents: list[tuple[str, list[str]]]) -> AgentSelector:
    reg = AgentRegistry()
    reg.clear()
    for aid, caps in agents:
        a = MockAgent(aid)
        a.config.capabilities = caps
        reg.register(a)
    return AgentSelector(reg)


class TestRePlannerBasic:

    @pytest.mark.asyncio
    async def test_no_failed_steps_returns_original(self):
        plan = _make_plan([("research", TaskType.RESEARCH)])
        feedback = FeedbackResult(success=True)
        replanner = RePlanner()

        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.intent == plan.intent
        assert len(new_plan.steps) == 1

    @pytest.mark.asyncio
    async def test_preserves_intent(self):
        plan = _make_plan([("research", TaskType.RESEARCH, "old-agent")])
        feedback = FeedbackResult(success=False, failed_steps=["research"])
        selector = _make_selector([("old-agent", ["research"]), ("new-agent", ["research"])])

        replanner = RePlanner(agent_selector=selector)
        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.intent == "test"


class TestRePlannerAgentReplacement:

    @pytest.mark.asyncio
    async def test_replaces_failed_agent(self):
        plan = _make_plan([("research", TaskType.RESEARCH, "bad-agent")])
        feedback = FeedbackResult(success=False, failed_steps=["research"])
        selector = _make_selector([("bad-agent", ["research"]), ("good-agent", ["research"])])

        replanner = RePlanner(agent_selector=selector)
        new_plan = await replanner.replan("task", plan, feedback)

        research_step = new_plan.steps[0]
        assert research_step.agent_hint == "good-agent"

    @pytest.mark.asyncio
    async def test_no_replacement_when_same_agent(self):
        plan = _make_plan([("research", TaskType.RESEARCH, "only-agent")])
        feedback = FeedbackResult(success=False, failed_steps=["research"])
        selector = _make_selector([("only-agent", ["research"])])

        replanner = RePlanner(agent_selector=selector)
        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.steps[0].agent_hint == "only-agent"

    @pytest.mark.asyncio
    async def test_no_selector_keeps_original(self):
        plan = _make_plan([("research", TaskType.RESEARCH, "agent-a")])
        feedback = FeedbackResult(success=False, failed_steps=["research"])

        replanner = RePlanner(agent_selector=None)
        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.steps[0].agent_hint == "agent-a"


class TestRePlannerMultiStep:

    @pytest.mark.asyncio
    async def test_only_replaces_failed_steps(self):
        plan = _make_plan([
            ("research", TaskType.RESEARCH, "r-agent"),
            ("writing", TaskType.WRITING, "w-agent"),
        ])
        feedback = FeedbackResult(success=False, failed_steps=["research"])
        selector = _make_selector([
            ("r-agent", ["research"]),
            ("new-r", ["research"]),
        ])

        replanner = RePlanner(agent_selector=selector)
        new_plan = await replanner.replan("task", plan, feedback)

        assert new_plan.steps[0].agent_hint == "new-r"
        assert new_plan.steps[1].agent_hint == "w-agent"

    @pytest.mark.asyncio
    async def test_preserves_dependencies(self):
        plan = _make_plan([
            ("research", TaskType.RESEARCH, "r-agent"),
            ("writing", TaskType.WRITING, "w-agent"),
        ])
        plan.steps[1].depends_on = ["research"]
        feedback = FeedbackResult(success=False, failed_steps=["research"])

        replanner = RePlanner()
        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.steps[1].depends_on == ["research"]

    @pytest.mark.asyncio
    async def test_preserves_context_query(self):
        plan = _make_plan([("research", TaskType.RESEARCH)])
        plan.context_query = "AI趋势"
        feedback = FeedbackResult(success=False, failed_steps=["research"])

        replanner = RePlanner()
        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.context_query == "AI趋势"

class TestRePlannerEdgeCases:

    @pytest.mark.asyncio
    async def test_multiple_failed_steps(self):
        plan = _make_plan([
            ("research", TaskType.RESEARCH, "r-agent"),
            ("writing", TaskType.WRITING, "w-agent"),
        ])
        feedback = FeedbackResult(success=False, failed_steps=["research", "writing"])
        selector = _make_selector([
            ("r-agent", ["research"]),
            ("w-agent", ["writing"]),
            ("new-r", ["research"]),
            ("new-w", ["writing"]),
        ])

        replanner = RePlanner(agent_selector=selector)
        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.steps[0].agent_hint == "new-r"
        assert new_plan.steps[1].agent_hint == "new-w"

    @pytest.mark.asyncio
    async def test_step_params_preserved(self):
        plan = _make_plan([("research", TaskType.RESEARCH, "agent")])
        plan.steps[0].params = {"capability": "research", "custom": True}
        feedback = FeedbackResult(success=False, failed_steps=["research"])

        replanner = RePlanner()
        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.steps[0].params["custom"] is True

    @pytest.mark.asyncio
    async def test_step_description_preserved(self):
        plan = _make_plan([("research", TaskType.RESEARCH, "agent")])
        feedback = FeedbackResult(success=False, failed_steps=["research"])

        replanner = RePlanner()
        new_plan = await replanner.replan("task", plan, feedback)
        assert new_plan.steps[0].description == "desc-research"