"""
Orchestrator 模块测试
"""

import pytest

from app.orchestrator.core import Orchestrator
from app.orchestrator.executor import StepStatus, TaskExecutor
from app.orchestrator.llm_provider import LLMMessage, LLMRole, MockLLMProvider
from app.orchestrator.planner import TaskPlanner, TaskType
from app.orchestrator.router import AgentRouter


class TestTaskPlanner:

    def test_classify_content_production(self):
        plan = TaskPlanner().plan("写一篇关于AI最新进展的文章")
        assert len(plan.steps) == 5
        assert plan.steps[0].type == TaskType.RESEARCH

    def test_classify_chat(self):
        plan = TaskPlanner().plan("你好")
        assert plan.steps[0].type == TaskType.CHAT

    def test_plan_dependencies(self):
        plan = TaskPlanner().plan("写一篇关于AI的文章")
        writing = next(s for s in plan.steps if s.id == "writing")
        assert "analysis" in writing.depends_on


class TestAgentRouter:

    def test_route_by_type(self):
        agent = AgentRouter().route("research")
        assert agent.id == "research-agent"

    def test_route_fallback(self):
        agent = AgentRouter().route("nonexistent")
        assert agent.id == "default-agent"


class TestTaskExecutor:

    @pytest.mark.asyncio
    async def test_execute_chat(self):
        from app.orchestrator.planner import TaskStep
        executor = TaskExecutor(AgentRouter())
        step = TaskStep(id="test", type=TaskType.CHAT, description="你好")
        result = await executor.execute(step)
        assert result.status == StepStatus.SUCCESS


class TestOrchestrator:

    @pytest.mark.asyncio
    async def test_run_returns_task_id(self):
        orch = Orchestrator()
        result = await orch.run("你好")
        assert result.task_id
        assert result.created_at

    @pytest.mark.asyncio
    async def test_run_content_pipeline(self):
        orch = Orchestrator()
        result = await orch.run("写一篇关于AI的文章")
        assert result.status in ("success", "partial")
        assert len(result.steps) == 5

    @pytest.mark.asyncio
    async def test_llm_provider(self):
        llm = MockLLMProvider()
        resp = await llm.chat([LLMMessage(role=LLMRole.USER, content="test")])
        assert "[Mock LLM]" in resp.content