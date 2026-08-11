"""
Phase 3.16 测试 — TaskLoopManager
"""

import pytest
from app.execution.task_loop import TaskLoopManager, LoopResult
from app.execution.history import ExecutionHistory
from app.planning.planner import Planner
from app.planning.replanner import RePlanner
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.agents.mock_agent import MockAgent


def _fail_then_succeed(fail_count: int):
    """创建前 N 次失败之后成功的 Agent"""
    class _Agent(MockAgent):
        def __init__(self):
            super().__init__("retry-agent")
            self._attempt = 0

        async def execute_step(self, step, context=None):
            self._attempt += 1
            self._call_log.append({"step_id": step.id, "task_type": step.type.value, "description": step.description})
            if self._attempt <= fail_count:
                raise RuntimeError("timeout")
            return self._build_output(step)

    return _Agent()


def _always_fail():
    class _Agent(MockAgent):
        async def execute_step(self, step, context=None):
            self._call_log.append({"step_id": step.id, "task_type": step.type.value, "description": step.description})
            raise RuntimeError("permanent failure")
    return _Agent("fail-agent")


class TestTaskLoopSuccess:

    @pytest.mark.asyncio
    async def test_first_attempt_success(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料", max_iterations=3)

        assert result.success is True
        assert result.iterations == 1
        assert len(result.history) == 1

    @pytest.mark.asyncio
    async def test_result_has_task_id(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料")
        assert result.task_id.startswith("task-")


class TestTaskLoopRetry:

    @pytest.mark.asyncio
    async def test_timeout_retries_and_succeeds(self):
        agent = _fail_then_succeed(fail_count=1)
        planner = Planner.from_registry()
        executor = PipelineExecutor(agent_map={"research": agent})
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料", max_iterations=3)

        assert result.success is True
        assert result.iterations >= 1

    @pytest.mark.asyncio
    async def test_max_iterations_returns_failure(self):
        agent = _always_fail()
        planner = Planner.from_registry()
        executor = PipelineExecutor(agent_map={"research": agent})
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料", max_iterations=2)

        assert result.success is False
        assert result.iterations == 2


class TestTaskLoopWithReplanner:

    @pytest.mark.asyncio
    async def test_replanner_called_on_failure(self):
        agent = _always_fail()
        planner = Planner.from_registry()
        executor = PipelineExecutor(agent_map={"research": agent})
        replanner = RePlanner()
        loop = TaskLoopManager(planner, executor, replanner=replanner)

        result = await loop.run("搜索资料", max_iterations=2)

        assert result.success is False
        assert len(result.history) == 2

    @pytest.mark.asyncio
    async def test_no_replanner_retries_same_plan(self):
        agent = _fail_then_succeed(fail_count=1)
        planner = Planner.from_registry()
        executor = PipelineExecutor(agent_map={"research": agent})
        loop = TaskLoopManager(planner, executor, replanner=None)

        result = await loop.run("搜索资料", max_iterations=3)
        assert result.success is True


class TestTaskLoopHistory:

    @pytest.mark.asyncio
    async def test_history_recorded(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        history = ExecutionHistory()
        loop = TaskLoopManager(planner, executor, history=history)

        result = await loop.run("搜索资料")

        assert history.total_entries >= 1
        entries = history.get_history(result.task_id)
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_loop_result_history(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料")
        assert len(result.history) >= 1
        assert result.history[0].success is True


class TestTaskLoopResult:

    @pytest.mark.asyncio
    async def test_loop_result_to_dict(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料")
        d = result.to_dict()

        assert "success" in d
        assert "iterations" in d
        assert "task_id" in d
        assert "history" in d

    @pytest.mark.asyncio
    async def test_history_property(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        history = ExecutionHistory()
        loop = TaskLoopManager(planner, executor, history=history)

        assert loop.history is history

    @pytest.mark.asyncio
    async def test_final_result_present(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料")
        assert result.final_result is not None

class TestTaskLoopEdgeCases:

    @pytest.mark.asyncio
    async def test_max_iterations_one(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料", max_iterations=1)
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_multi_step_success(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("研究趋势并写报告", max_iterations=2)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_history_preserved_across_iterations(self):
        agent = _fail_then_succeed(fail_count=1)
        planner = Planner.from_registry()
        executor = PipelineExecutor(agent_map={"research": agent})
        history = ExecutionHistory()
        loop = TaskLoopManager(planner, executor, history=history)

        result = await loop.run("搜索资料", max_iterations=3)
        entries = history.get_history(result.task_id)
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_iteration_record_to_dict(self):
        planner = Planner.from_registry()
        executor = PipelineExecutor()
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料")
        d = result.history[0].to_dict()
        assert "iteration" in d
        assert "success" in d
        assert "status" in d

    @pytest.mark.asyncio
    async def test_loop_with_memory(self):
        from app.memory.experience import ExperienceMemory
        exp = ExperienceMemory()
        planner = Planner.from_registry()
        executor = PipelineExecutor(experience=exp)
        loop = TaskLoopManager(planner, executor)

        result = await loop.run("搜索资料")
        assert exp.total_records >= 1