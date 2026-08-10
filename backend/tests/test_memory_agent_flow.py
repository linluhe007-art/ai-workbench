"""
Memory-Augmented Agent Flow 测试
覆盖：AgentContext 注入、Memory 查询、结果回写、端到端 pipeline。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.orchestrator.pipeline_executor import PipelineExecutor, ExecutionResult
from app.orchestrator.executor import StepStatus
from app.agents.context import AgentContext
from app.agents.mock_agent import MockAgent
from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentType, AgentStatus


# === AgentContext 测试 ===

class TestAgentContext:

    def test_default_context(self):
        ctx = AgentContext()
        assert ctx.documents == []
        assert ctx.tags == []
        assert ctx.memory_summary == ""
        assert ctx.upstream_results == {}

    def test_context_with_memory(self):
        ctx = AgentContext(
            documents=[{"title": "doc1"}],
            tags=["AI", "tech"],
            memory_summary="相关知识摘要",
            agent_type="research",
        )
        assert len(ctx.documents) == 1
        assert "AI" in ctx.tags
        assert ctx.agent_type == "research"

    def test_context_to_dict(self):
        ctx = AgentContext(
            documents=[{"title": "d1"}, {"title": "d2"}],
            tags=["tag1"],
            upstream_results={"step1": {"data": 1}},
        )
        d = ctx.to_dict()
        assert d["documents_count"] == 2
        assert d["tags"] == ["tag1"]
        assert "step1" in d["upstream_steps"]


# === Memory 注入测试 ===

class TestMemoryInjection:

    @pytest.mark.asyncio
    async def test_context_passed_to_agent(self):
        """验证 AgentContext 被传递到 execute_step"""
        received_ctx = {}

        class _CaptureAgent(MockAgent):
            async def execute_step(self, step, context=None):
                received_ctx["ctx"] = context
                return {"captured": True}

        agent = _CaptureAgent("cap")
        plan = TaskPlan(intent="test", steps=[
            TaskStep(id="s1", type=TaskType.CHAT, description="test"),
        ])

        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute(plan)

        assert result.status == "success"
        assert received_ctx["ctx"] is not None
        assert isinstance(received_ctx["ctx"], AgentContext)

    @pytest.mark.asyncio
    async def test_memory_context_injected(self):
        """验证 Memory 上下文被注入到 AgentContext"""
        mock_memory = MagicMock()
        mock_memory.get_memory_context = MagicMock(return_value=MagicMock(
            documents=[{"title": "知识库文档"}],
            tags=["AI", "创作"],
            related_links=["[[链接1]]"],
            summary="知识库摘要内容",
        ))

        received_ctx = {}

        class _CaptureAgent(MockAgent):
            async def execute_step(self, step, context=None):
                received_ctx["ctx"] = context
                return {"ok": True}

        agent = _CaptureAgent("cap")
        plan = TaskPlan(
            intent="写AI文章",
            steps=[TaskStep(id="s1", type=TaskType.WRITING, description="写文章")],
            context_query="AI",
        )

        executor = PipelineExecutor(
            agent_map={"s1": agent},
            memory_service=mock_memory,
        )
        result = await executor.execute(plan)

        assert result.status == "success"
        ctx = received_ctx["ctx"]
        assert ctx.memory_summary == "知识库摘要内容"
        assert len(ctx.documents) > 0
        mock_memory.get_memory_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_failure_does_not_block(self):
        """Memory 查询失败不应阻塞执行"""
        mock_memory = MagicMock()
        mock_memory.get_memory_context = MagicMock(side_effect=RuntimeError("Memory unavailable"))

        agent = MockAgent("safe")
        plan = TaskPlan(
            intent="test",
            steps=[TaskStep(id="s1", type=TaskType.CHAT, description="test")],
            context_query="test",
        )

        executor = PipelineExecutor(
            agent_map={"s1": agent},
            memory_service=mock_memory,
        )
        result = await executor.execute(plan)

        # 应该正常完成，即使 Memory 失败
        assert result.status == "success"
        assert result.step_results["s1"].status == StepStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_no_memory_service_still_works(self):
        """没有 MemoryService 时正常执行"""
        agent = MockAgent("nomem")
        plan = TaskPlan(intent="test", steps=[
            TaskStep(id="s1", type=TaskType.CHAT, description="test"),
        ])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute(plan)

        assert result.status == "success"
        # memory_contexts 应为空 AgentContext
        ctx = result.memory_contexts.get("s1")
        assert ctx is not None
        assert ctx.documents == []


# === 上下文传递测试 ===

class TestUpstreamContext:

    @pytest.mark.asyncio
    async def test_upstream_results_in_context(self):
        """上游步骤输出应出现在 downstream 的 AgentContext 中"""
        received_ctx = {}

        class _CaptureAgent(MockAgent):
            async def execute_step(self, step, context=None):
                if step.id == "s2":
                    received_ctx["ctx"] = context
                return {"step": step.id}

        agent = _CaptureAgent("cap")
        plan = TaskPlan(intent="test", steps=[
            TaskStep(id="s1", type=TaskType.RESEARCH, description="采集"),
            TaskStep(id="s2", type=TaskType.WRITING, description="写作", depends_on=["s1"]),
        ])

        executor = PipelineExecutor(agent_map={"s1": agent, "s2": agent})
        result = await executor.execute(plan)

        assert result.status == "success"
        ctx = received_ctx["ctx"]
        assert "s1" in ctx.upstream_results
        assert ctx.upstream_results["s1"]["step"] == "s1"


# === 端到端 Pipeline 测试 ===

class TestMemoryAugmentedPipeline:

    @pytest.mark.asyncio
    async def test_full_pipeline_with_memory(self):
        """完整 5 步 pipeline + Memory 注入"""
        mock_memory = MagicMock()
        mock_memory.get_memory_context = MagicMock(return_value=MagicMock(
            documents=[{"title": "参考文档"}],
            tags=["AI"],
            related_links=[],
            summary="参考摘要",
        ))

        agent = MockAgent("full")
        plan = TaskPlan(
            intent="写AI新闻",
            steps=[
                TaskStep(id="research", type=TaskType.RESEARCH, description="采集"),
                TaskStep(id="analysis", type=TaskType.ANALYSIS, description="分析", depends_on=["research"]),
                TaskStep(id="writing", type=TaskType.WRITING, description="写作", depends_on=["analysis"]),
                TaskStep(id="image", type=TaskType.IMAGE, description="封面", depends_on=["analysis"]),
                TaskStep(id="seo", type=TaskType.SEO, description="SEO", depends_on=["writing"]),
            ],
            context_query="AI",
        )

        executor = PipelineExecutor(
            agent_map={"default": agent},
            memory_service=mock_memory,
        )
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 5
        # Memory 应该被查询 5 次 (每个步骤一次)
        assert mock_memory.get_memory_context.call_count == 5
        # 所有步骤都有 memory_contexts
        assert len(result.memory_contexts) == 5

    @pytest.mark.asyncio
    async def test_execution_result_has_memory_contexts(self):
        """ExecutionResult 包含每个步骤的 AgentContext"""
        agent = MockAgent("ctx-check")
        plan = TaskPlan(intent="test", steps=[
            TaskStep(id="s1", type=TaskType.CHAT, description="test"),
        ])
        executor = PipelineExecutor(agent_map={"s1": agent})
        result = await executor.execute(plan)

        assert "s1" in result.memory_contexts
        assert isinstance(result.memory_contexts["s1"], AgentContext)