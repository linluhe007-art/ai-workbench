"""
Phase 3.18 - Observability Integration Tests
"""

import pytest
from app.agents.runtime import AgentRuntime, AgentState
from app.agents.mock_agent import MockAgent
from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.observability.collector import TraceCollector
from app.observability.metrics import RuntimeMetrics


def _make_plan(intent="test", steps=1):
    return TaskPlan(
        intent=intent,
        steps=[TaskStep(id=f"step-{i}", type=TaskType.CUSTOM, description=f"step {i}") for i in range(steps)],
    )


class TestAgentRuntimeTrace:
    async def test_run_agent_records_trace(self):
        collector = TraceCollector()
        runtime = AgentRuntime(trace_collector=collector)
        agent = MockAgent(agent_id="mock-1")
        runtime.register(agent)
        result = await runtime.run_agent("mock-1", "do something")
        events = collector.get_trace("mock-1")
        assert len(events) >= 2
        types = [e["event_type"] for e in events]
        assert "start" in types
        assert "end" in types

    async def test_run_agent_error_no_agent(self):
        collector = TraceCollector()
        runtime = AgentRuntime(trace_collector=collector)
        result = await runtime.run_agent("missing", "task")
        assert not result.success

    async def test_set_trace_collector_after_init(self):
        runtime = AgentRuntime()
        collector = TraceCollector()
        runtime.set_trace_collector(collector)
        assert runtime._trace is collector

    async def test_no_trace_backward_compat(self):
        runtime = AgentRuntime()
        agent = MockAgent(agent_id="mock-1")
        runtime.register(agent)
        result = await runtime.run_agent("mock-1", "task")
        assert result.success

    async def test_run_agent_success_state(self):
        collector = TraceCollector()
        runtime = AgentRuntime(trace_collector=collector)
        agent = MockAgent(agent_id="mock-1")
        runtime.register(agent)
        result = await runtime.run_agent("mock-1", "task")
        assert result.success
        assert runtime.get_state("mock-1") == AgentState.COMPLETED
        assert collector.total_events >= 2

    async def test_run_parallel_traces(self):
        collector = TraceCollector()
        runtime = AgentRuntime(trace_collector=collector)
        a1 = MockAgent(agent_id="a1")
        a2 = MockAgent(agent_id="a2")
        runtime.register(a1)
        runtime.register(a2)
        results = await runtime.run_parallel([("a1", "task1"), ("a2", "task2")])
        assert len(results) == 2
        assert collector.total_events >= 4


class TestPipelineExecutorTrace:
    async def test_execute_records_trace(self):
        collector = TraceCollector()
        agent = MockAgent(agent_id="default")
        executor = PipelineExecutor(agent_map={"default": agent}, trace_collector=collector)
        plan = _make_plan("test-task", 1)
        result = await executor.execute(plan)
        events = collector.get_trace("test-task")
        assert len(events) >= 3
        types = [e["event_type"] for e in events]
        assert "start" in types
        assert "end" in types

    async def test_execute_error_trace(self):
        collector = TraceCollector()
        class FailAgent(MockAgent):
            async def execute_step(self, step, context=None):
                raise RuntimeError("boom")
        agent = FailAgent(agent_id="failing")
        executor = PipelineExecutor(agent_map={"default": agent}, trace_collector=collector)
        plan = _make_plan("fail-task", 1)
        result = await executor.execute(plan)
        errors = collector.get_errors(task_id="fail-task")
        assert len(errors) >= 1

    async def test_parallel_steps_trace(self):
        collector = TraceCollector()
        agent = MockAgent(agent_id="default")
        executor = PipelineExecutor(agent_map={"default": agent}, trace_collector=collector)
        plan = _make_plan("par-task", 2)
        result = await executor.execute(plan)
        assert len(collector.get_trace("par-task")) >= 5

    async def test_set_trace_after_init(self):
        executor = PipelineExecutor()
        collector = TraceCollector()
        executor.set_trace_collector(collector)
        assert executor._trace is collector

    async def test_no_trace_compat(self):
        agent = MockAgent(agent_id="default")
        executor = PipelineExecutor(agent_map={"default": agent})
        plan = _make_plan("no-trace", 1)
        result = await executor.execute(plan)
        assert result.status == "success"

    async def test_dag_trace(self):
        collector = TraceCollector()
        agent = MockAgent(agent_id="default")
        executor = PipelineExecutor(agent_map={"default": agent}, trace_collector=collector)
        plan = TaskPlan(intent="dag-task", steps=[
            TaskStep(id="s1", type=TaskType.CUSTOM, description="first"),
            TaskStep(id="s2", type=TaskType.CUSTOM, description="second", depends_on=["s1"]),
            TaskStep(id="s3", type=TaskType.CUSTOM, description="third", depends_on=["s2"]),
        ])
        result = await executor.execute(plan)
        assert result.status == "success"
        assert len(collector.get_trace("dag-task")) >= 6


class TestTaskLoopTrace:
    def _make_loop(self):
        from app.planning.planner import Planner
        collector = TraceCollector()
        agent = MockAgent(agent_id="default")
        executor = PipelineExecutor(agent_map={"default": agent}, trace_collector=collector)
        planner = Planner.from_registry()
        from app.execution.task_loop import TaskLoopManager
        loop = TaskLoopManager(planner, executor, trace_collector=collector)
        return loop, collector

    async def test_loop_start_end(self):
        loop, collector = self._make_loop()
        result = await loop.run("搜索资料", max_iterations=1)
        loop_events = [e for e in collector._events if e.component == "loop"]
        assert len(loop_events) >= 2
        types = [e.event_type for e in loop_events]
        assert "start" in types
        assert "end" in types

    async def test_loop_iteration_metric(self):
        loop, collector = self._make_loop()
        result = await loop.run("搜索资料", max_iterations=1)
        iter_metrics = [e for e in collector._events if e.event_type == "metric" and e.metadata.get("metric_name") == "iteration"]
        assert len(iter_metrics) >= 1

    async def test_loop_no_trace_compat(self):
        from app.planning.planner import Planner
        from app.execution.task_loop import TaskLoopManager
        agent = MockAgent(agent_id="default")
        executor = PipelineExecutor(agent_map={"default": agent})
        planner = Planner.from_registry()
        loop = TaskLoopManager(planner, executor)
        result = await loop.run("搜索资料", max_iterations=1)
        assert result.iterations >= 1

    async def test_loop_success_trace(self):
        loop, collector = self._make_loop()
        result = await loop.run("搜索资料", max_iterations=1)
        assert result.success
        end_events = [e for e in collector._events if e.component == "loop" and e.event_type == "end"]
        assert len(end_events) >= 1
        assert end_events[0].metadata.get("success") is True


class TestMetricsIntegration:
    def test_full_trace_metrics(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "loop")
        collector.start("t1", "task-1", "agent", metadata={"agent_id": "research"})
        collector.end("t1", "task-1", "agent", duration_ms=100, metadata={"success": True})
        collector.start("t1", "task-1", "executor")
        collector.end("t1", "task-1", "executor", duration_ms=200, metadata={"step_id": "s1", "success": True})
        collector.start("t1", "task-1", "executor")
        collector.end("t1", "task-1", "executor", duration_ms=150, metadata={"step_id": "s2", "success": True})
        collector.metric("t1", "task-1", "loop", "eval_score", 8.5)
        collector.end("t1", "task-1", "loop", duration_ms=500, metadata={"success": True})
        metrics = RuntimeMetrics(collector).compute()
        assert metrics["total_tasks"] == 1
        assert metrics["success_rate"] == 1.0
        assert metrics["agent_runs"] == 1
        assert metrics["total_steps"] == 2
        assert metrics["step_failure_rate"] == 0.0
        assert metrics["total_errors"] == 0

    def test_multi_task_metrics(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "loop")
        collector.end("t1", "task-1", "loop", duration_ms=200, metadata={"success": True})
        collector.start("t2", "task-2", "loop")
        collector.error("t2", "task-2", "agent", error="timeout")
        collector.end("t2", "task-2", "loop", duration_ms=300, metadata={"success": False})
        metrics = RuntimeMetrics(collector).compute()
        assert metrics["total_tasks"] == 2
        assert metrics["success_rate"] == 0.5
        assert metrics["total_errors"] >= 1

    def test_events_serializable(self):
        collector = TraceCollector()
        collector.start("t1", "task-1", "executor")
        collector.end("t1", "task-1", "executor", duration_ms=100)
        collector.error("t1", "task-1", "agent", error="e")
        collector.metric("t1", "task-1", "loop", "score", 7.0)
        for event in collector._events:
            d = event.to_dict()
            assert isinstance(d, dict)
            assert "trace_id" in d
            assert "timestamp" in d