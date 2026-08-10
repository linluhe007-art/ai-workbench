"""
Agent Registry 测试
覆盖：注册、查找、执行、全局单例。
"""

import pytest

from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentResult, AgentType, AgentStatus
from app.agents.registry import AgentRegistry
from app.agents.mock_agent import MockAgent


class TestAgentRegistry:

    def test_register_and_get(self):
        reg = AgentRegistry()
        agent = MockAgent("test-1")
        reg.register(agent)

        found = reg.get("test-1")
        assert found is agent

    def test_get_by_name(self):
        reg = AgentRegistry()
        agent = MockAgent("my-id")
        reg.register(agent)

        # get() 优先匹配 id
        assert reg.get("my-id") is agent

    def test_get_nonexistent(self):
        reg = AgentRegistry()
        assert reg.get("nope") is None

    def test_list_agents(self):
        reg = AgentRegistry()
        reg.register(MockAgent("a1"))
        reg.register(MockAgent("a2"))

        agents = reg.list_agents()
        assert len(agents) == 2
        ids = {a["id"] for a in agents}
        assert ids == {"a1", "a2"}

    def test_unregister(self):
        reg = AgentRegistry()
        reg.register(MockAgent("x"))
        assert reg.unregister("x") is True
        assert reg.get("x") is None
        assert reg.unregister("x") is False

    def test_clear(self):
        reg = AgentRegistry()
        reg.register(MockAgent("a"))
        reg.register(MockAgent("b"))
        reg.clear()
        assert len(reg) == 0

    def test_contains(self):
        reg = AgentRegistry()
        reg.register(MockAgent("z"))
        assert "z" in reg
        assert "nope" not in reg

    def test_overwrite_warning(self):
        reg = AgentRegistry()
        reg.register(MockAgent("dup"))
        reg.register(MockAgent("dup"))  # 不应报错，只 warning
        assert len(reg) == 1


class TestBaseAgentNewInterface:

    @pytest.mark.asyncio
    async def test_agent_result_success(self):
        agent = MockAgent("r1")
        result = await agent.execute("帮我写文章")

        assert isinstance(result, AgentResult)
        assert result.success is True
        assert result.error == ""

    @pytest.mark.asyncio
    async def test_agent_result_with_context(self):
        agent = MockAgent("r2")
        result = await agent.execute("分析数据", context={"source": "test"})

        assert result.success is True
        assert isinstance(result.output, dict)

    def test_description_property(self):
        agent = MockAgent("d1")
        # 默认 description
        assert "Mock(d1)" in agent.description

    def test_description_from_extra(self):
        config = AgentConfig(
            id="d2", name="D2", type=AgentType.CUSTOM,
            extra={"description": "自定义描述"},
        )

        class _Agent(BaseAgent):
            async def chat(self, message, context=None):
                return ""
            async def execute_task(self, task_input):
                return AgentResponse(success=True)
            def get_capabilities(self):
                return []

        agent = _Agent(config)
        assert agent.description == "自定义描述"


class TestMockAgentExecuteStep:

    @pytest.mark.asyncio
    async def test_execute_step_default(self):
        from app.orchestrator.planner import TaskStep, TaskType
        agent = MockAgent("s1")
        step = TaskStep(id="t1", type=TaskType.CHAT, description="测试步骤")
        output = await agent.execute_step(step)

        assert output["step_id"] == "t1"
        assert "已完成" in output["result"]

    @pytest.mark.asyncio
    async def test_execute_step_preset(self):
        from app.orchestrator.planner import TaskStep, TaskType
        agent = MockAgent("s2")
        agent.set_response("t1", {"custom": True})
        step = TaskStep(id="t1", type=TaskType.CHAT, description="test")
        output = await agent.execute_step(step)

        assert output == {"custom": True}

    @pytest.mark.asyncio
    async def test_call_log(self):
        from app.orchestrator.planner import TaskStep, TaskType
        agent = MockAgent("s3")
        step = TaskStep(id="t1", type=TaskType.RESEARCH, description="采集")
        await agent.execute_step(step)

        assert len(agent.call_log) == 1
        assert agent.call_log[0]["step_id"] == "t1"