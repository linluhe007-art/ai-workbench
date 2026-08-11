"""
Phase 3.8 测试 — AgentRuntime + Parallel Pipeline
覆盖：
- AgentRuntime 注册/获取/列表
- Agent 生命周期 (initialize/shutdown)
- Agent 状态管理 (IDLE/RUNNING/COMPLETED/FAILED)
- Agent 间消息路由
- AgentRuntime run_agent / run_parallel
- PipelineExecutor 并行 DAG 执行
- 并行分支失败隔离
"""

import asyncio
import pytest

from app.agents.runtime import AgentRuntime, AgentState
from app.agents.message import AgentMessage
from app.agents.mock_agent import MockAgent
from app.agents.base import AgentType
from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.orchestrator.pipeline_executor import PipelineExecutor, ExecutionResult
from app.orchestrator.executor import StepStatus


# ─── helpers ───────────────────────────────────────────────

def _make_runtime_with_agents(count: int = 3) -> tuple[AgentRuntime, list[MockAgent]]:
    runtime = AgentRuntime()
    agents = []
    for i in range(count):
        agent = MockAgent(agent_id=f"agent-{i}")
        runtime.register(agent)
        agents.append(agent)
    return runtime, agents


def _make_plan(steps: list[tuple]) -> TaskPlan:
    """
    快捷构建 TaskPlan
    steps: [(id, type, [depends_on]), ...]
    """
    task_steps = []
    for item in steps:
        sid, stype = item[0], item[1]
        deps = item[2] if len(item) > 2 else []
        task_steps.append(TaskStep(
            id=sid, type=stype, description=f"desc-{sid}", depends_on=deps,
        ))
    return TaskPlan(intent="test", steps=task_steps)


def _slow_agent(agent_id: str, delay: float = 0.05) -> MockAgent:
    """返回一个有延迟的 Agent（用于验证并行执行）"""

    class _SlowAgent(MockAgent):
        async def execute_step(self, step: TaskStep, context=None) -> dict:
            self._call_log.append({
                "step_id": step.id,
                "task_type": step.type.value,
                "description": step.description,
            })
            await asyncio.sleep(delay)
            return self._build_output(step)

    return _SlowAgent(agent_id=agent_id)


def _failing_agent(agent_id: str, error_msg: str = "boom") -> MockAgent:
    """返回一个会抛异常的 Agent"""

    class _FailAgent(MockAgent):
        async def execute_step(self, step: TaskStep, context=None) -> dict:
            self._call_log.append({
                "step_id": step.id,
                "task_type": step.type.value,
                "description": step.description,
            })
            raise RuntimeError(error_msg)

    return _FailAgent(agent_id=agent_id)


# ═══════════════════════════════════════════════════════════
# AgentRuntime 测试
# ═══════════════════════════════════════════════════════════


class TestAgentRegistration:
    """Agent 注册与获取"""

    def test_register_and_get(self):
        runtime = AgentRuntime()
        agent = MockAgent("a1")
        runtime.register(agent)

        assert runtime.get("a1") is agent
        assert runtime.get("nonexistent") is None

    def test_list_agents(self):
        runtime, agents = _make_runtime_with_agents(3)
        listed = runtime.list_agents()

        assert len(listed) == 3
        ids = {a["id"] for a in listed}
        assert ids == {"agent-0", "agent-1", "agent-2"}

    def test_list_agents_shows_state(self):
        runtime, _ = _make_runtime_with_agents(1)
        listed = runtime.list_agents()

        assert listed[0]["state"] == "idle"


class TestAgentLifecycle:
    """Agent 生命周期"""

    @pytest.mark.asyncio
    async def test_initialize_agent(self):
        runtime, agents = _make_runtime_with_agents(1)
        await runtime.initialize_agent("agent-0")

        assert agents[0].status.value == "online"

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        runtime, agents = _make_runtime_with_agents(3)
        await runtime.initialize_all()

        for a in agents:
            assert a.status.value == "online"

    @pytest.mark.asyncio
    async def test_shutdown_agent(self):
        runtime, agents = _make_runtime_with_agents(1)
        await runtime.initialize_all()
        await runtime.shutdown_agent("agent-0")

        assert agents[0].status.value == "offline"

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        runtime, agents = _make_runtime_with_agents(3)
        await runtime.initialize_all()
        await runtime.shutdown_all()

        for a in agents:
            assert a.status.value == "offline"


class TestAgentStateManagement:
    """状态追踪"""

    def test_initial_state_is_idle(self):
        runtime, _ = _make_runtime_with_agents(1)
        assert runtime.get_state("agent-0") == AgentState.IDLE

    def test_set_state_running(self):
        runtime, _ = _make_runtime_with_agents(1)
        runtime.set_state("agent-0", AgentState.RUNNING)

        assert runtime.get_state("agent-0") == AgentState.RUNNING
        record = runtime.get_record("agent-0")
        assert record.started_at is not None

    def test_set_state_completed(self):
        runtime, _ = _make_runtime_with_agents(1)
        runtime.set_state("agent-0", AgentState.RUNNING)
        runtime.set_state("agent-0", AgentState.COMPLETED)

        assert runtime.get_state("agent-0") == AgentState.COMPLETED
        record = runtime.get_record("agent-0")
        assert record.completed_at is not None

    def test_set_state_nonexistent(self):
        runtime = AgentRuntime()
        runtime.set_state("ghost", AgentState.RUNNING)
        assert runtime.get_state("ghost") is None

    def test_get_record(self):
        runtime, _ = _make_runtime_with_agents(1)
        record = runtime.get_record("agent-0")

        assert record is not None
        assert record.agent_id == "agent-0"
        assert record.state == AgentState.IDLE


class TestAgentMessageRouting:
    """Agent 间消息路由"""

    def test_send_and_receive(self):
        runtime, _ = _make_runtime_with_agents(2)
        msg = AgentMessage(
            sender="agent-0",
            receiver="agent-1",
            content={"data": "hello"},
            msg_type="data",
        )
        runtime.send_message(msg)

        messages = runtime.receive_messages("agent-1")
        assert len(messages) == 1
        assert messages[0].content == {"data": "hello"}
        assert messages[0].sender == "agent-0"

    def test_receive_clears_queue(self):
        runtime, _ = _make_runtime_with_agents(2)
        msg = AgentMessage(sender="agent-0", receiver="agent-1", content="test")
        runtime.send_message(msg)

        runtime.receive_messages("agent-1")
        assert len(runtime.receive_messages("agent-1")) == 0

    def test_peek_does_not_clear(self):
        runtime, _ = _make_runtime_with_agents(2)
        msg = AgentMessage(sender="agent-0", receiver="agent-1", content="test")
        runtime.send_message(msg)

        peeked = runtime.peek_messages("agent-1")
        assert len(peeked) == 1

        still = runtime.peek_messages("agent-1")
        assert len(still) == 1

    def test_message_to_nonexistent_agent(self):
        runtime = AgentRuntime()
        msg = AgentMessage(sender="a", receiver="ghost", content="data")
        runtime.send_message(msg)

        messages = runtime.receive_messages("ghost")
        assert len(messages) == 0

    def test_multiple_messages(self):
        runtime, _ = _make_runtime_with_agents(2)
        for i in range(5):
            runtime.send_message(AgentMessage(
                sender="agent-0", receiver="agent-1", content={"i": i},
            ))

        messages = runtime.receive_messages("agent-1")
        assert len(messages) == 5
        assert [m.content["i"] for m in messages] == [0, 1, 2, 3, 4]

    def test_message_to_dict(self):
        msg = AgentMessage(
            sender="a", receiver="b", content="test", msg_type="data",
        )
        d = msg.to_dict()

        assert d["sender"] == "a"
        assert d["receiver"] == "b"
        assert d["msg_type"] == "data"
        assert "timestamp" in d


class TestAgentRuntimeExecution:
    """run_agent / run_parallel"""

    @pytest.mark.asyncio
    async def test_run_agent_success(self):
        runtime, agents = _make_runtime_with_agents(1)
        result = await runtime.run_agent("agent-0", "say hello")

        assert result.success is True
        assert runtime.get_state("agent-0") == AgentState.COMPLETED

    @pytest.mark.asyncio
    async def test_run_agent_not_found(self):
        runtime = AgentRuntime()
        result = await runtime.run_agent("ghost", "task")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_agent_failure_state(self):
        runtime = AgentRuntime()
        agent = _failing_agent("fail-1")
        runtime.register(agent)

        result = await runtime.run_agent("fail-1", "boom task")

        assert result.success is False
        assert runtime.get_state("fail-1") == AgentState.FAILED

    @pytest.mark.asyncio
    async def test_run_parallel(self):
        runtime, _ = _make_runtime_with_agents(3)
        tasks = [
            ("agent-0", "task-a"),
            ("agent-1", "task-b"),
            ("agent-2", "task-c"),
        ]
        results = await runtime.run_parallel(tasks)

        assert len(results) == 3
        for aid in ("agent-0", "agent-1", "agent-2"):
            assert aid in results
            assert results[aid].success is True
            assert runtime.get_state(aid) == AgentState.COMPLETED

    @pytest.mark.asyncio
    async def test_run_parallel_mixed_results(self):
        runtime = AgentRuntime()
        good = MockAgent("good")
        bad = _failing_agent("bad")
        runtime.register(good)
        runtime.register(bad)

        results = await runtime.run_parallel([
            ("good", "ok task"),
            ("bad", "fail task"),
        ])

        assert results["good"].success is True
        assert results["bad"].success is False

    @pytest.mark.asyncio
    async def test_run_parallel_is_concurrent(self):
        """验证并行执行的时间应小于串行总和"""
        runtime = AgentRuntime()
        a1 = _slow_agent("s1", delay=0.1)
        a2 = _slow_agent("s2", delay=0.1)
        a3 = _slow_agent("s3", delay=0.1)
        runtime.register(a1)
        runtime.register(a2)
        runtime.register(a3)

        import time
        start = time.monotonic()
        results = await runtime.run_parallel([
            ("s1", "t1"), ("s2", "t2"), ("s3", "t3"),
        ])
        elapsed = time.monotonic() - start

        assert all(r.success for r in results.values())
        # 3 个 0.1s 的任务并行应 < 0.3s，留余量取 0.25s
        assert elapsed < 0.25, f"Parallel took {elapsed:.2f}s, expected < 0.25s"


# ═══════════════════════════════════════════════════════════
# PipelineExecutor 并行 DAG 测试
# ═══════════════════════════════════════════════════════════


class TestParallelPipelineExecution:
    """PipelineExecutor DAG 并行调度"""

    @pytest.mark.asyncio
    async def test_parallel_steps_are_concurrent(self):
        """
        research 和 analysis 无依赖应并行。
        3 个 0.1s 步骤并行应 < 0.25s。
        """
        plan = _make_plan([
            ("a", TaskType.RESEARCH),
            ("b", TaskType.ANALYSIS),
            ("c", TaskType.WRITING),
        ])
        agent_a = _slow_agent("slow-a", delay=0.1)
        agent_b = _slow_agent("slow-b", delay=0.1)
        agent_c = _slow_agent("slow-c", delay=0.1)

        executor = PipelineExecutor(agent_map={
            "a": agent_a, "b": agent_b, "c": agent_c,
        })

        import time
        start = time.monotonic()
        result = await executor.execute(plan)
        elapsed = time.monotonic() - start

        assert result.status == "success"
        assert result.success_count == 3
        assert elapsed < 0.25, f"Parallel pipeline took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_dependent_steps_run_after_deps(self):
        """
        research -> analysis -> writing 必须串行。
        analysis 必须在 research 完成后才开始。
        """
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
        ])
        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        # 验证时间顺序
        r = result.step_results["research"]
        a = result.step_results["analysis"]
        w = result.step_results["writing"]
        assert r.completed_at <= a.started_at
        assert a.completed_at <= w.started_at

    @pytest.mark.asyncio
    async def test_parallel_branches_after_dependency(self):
        """
        research -> analysis，然后 writing 和 image 并行。
        """
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
            ("image", TaskType.IMAGE, ["analysis"]),
        ])
        agent_w = _slow_agent("w", delay=0.1)
        agent_i = _slow_agent("i", delay=0.1)

        executor = PipelineExecutor(agent_map={
            "writing": agent_w, "image": agent_i,
        })

        import time
        start = time.monotonic()
        result = await executor.execute(plan)
        elapsed = time.monotonic() - start

        assert result.status == "success"
        assert result.success_count == 4
        # writing 和 image 并行，总时间应小于串行
        assert elapsed < 0.35

    @pytest.mark.asyncio
    async def test_full_5step_pipeline_parallel(self):
        """
        完整 5 步 pipeline: research -> analysis -> (writing, image) -> seo
        writing 和 image 应并行。
        """
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
            ("image", TaskType.IMAGE, ["analysis"]),
            ("seo", TaskType.SEO, ["writing"]),
        ])
        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 5
        # seo 依赖 writing，不在 image 之前
        w = result.step_results["writing"]
        s = result.step_results["seo"]
        assert w.completed_at <= s.started_at

    @pytest.mark.asyncio
    async def test_parallel_branch_failure_isolation(self):
        """并行分支中一个失败不影响其他分支"""
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("analysis", TaskType.ANALYSIS, ["research"]),
            ("writing", TaskType.WRITING, ["analysis"]),
            ("image", TaskType.IMAGE, ["analysis"]),
        ])
        executor = PipelineExecutor(agent_map={
            "image": _failing_agent("img-fail"),
        })
        result = await executor.execute(plan)

        assert result.step_results["image"].status == StepStatus.FAILED
        assert result.step_results["writing"].status == StepStatus.SUCCESS
        assert result.status == "partial"

    @pytest.mark.asyncio
    async def test_all_parallel_no_deps(self):
        """所有步骤无依赖 → 全部并行"""
        plan = _make_plan([
            ("a", TaskType.RESEARCH),
            ("b", TaskType.ANALYSIS),
            ("c", TaskType.WRITING),
        ])
        executor = PipelineExecutor()
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 3

    @pytest.mark.asyncio
    async def test_diamond_dag(self):
        """
        菱形依赖 (diamond DAG):
         A -> B, A -> C, B -> D, C -> D
        B、C 并行；D 等 B、C 都完成。
        """
        plan = _make_plan([
            ("a", TaskType.RESEARCH),
            ("b", TaskType.ANALYSIS, ["a"]),
            ("c", TaskType.IMAGE, ["a"]),
            ("d", TaskType.WRITING, ["b", "c"]),
        ])
        agent_b = _slow_agent("b-agent", delay=0.05)
        agent_c = _slow_agent("c-agent", delay=0.05)

        executor = PipelineExecutor(agent_map={
            "b": agent_b, "c": agent_c,
        })
        result = await executor.execute(plan)

        assert result.status == "success"
        assert result.success_count == 4
        # D 必须在 B、C 之后
        b = result.step_results["b"]
        c = result.step_results["c"]
        d = result.step_results["d"]
        assert b.completed_at <= d.started_at
        assert c.completed_at <= d.started_at


class TestTopologicalLevels:
    """_topological_levels 静态方法测试"""

    def test_all_independent(self):
        steps = [
            TaskStep(id="a", type=TaskType.RESEARCH, description=""),
            TaskStep(id="b", type=TaskType.ANALYSIS, description=""),
            TaskStep(id="c", type=TaskType.WRITING, description=""),
        ]
        levels = PipelineExecutor._topological_levels(steps)

        assert len(levels) == 1
        assert len(levels[0]) == 3

    def test_linear_chain(self):
        steps = [
            TaskStep(id="a", type=TaskType.RESEARCH, description=""),
            TaskStep(id="b", type=TaskType.ANALYSIS, description="", depends_on=["a"]),
            TaskStep(id="c", type=TaskType.WRITING, description="", depends_on=["b"]),
        ]
        levels = PipelineExecutor._topological_levels(steps)

        assert len(levels) == 3
        assert [s.id for s in levels[0]] == ["a"]
        assert [s.id for s in levels[1]] == ["b"]
        assert [s.id for s in levels[2]] == ["c"]

    def test_diamond(self):
        steps = [
            TaskStep(id="a", type=TaskType.RESEARCH, description=""),
            TaskStep(id="b", type=TaskType.ANALYSIS, description="", depends_on=["a"]),
            TaskStep(id="c", type=TaskType.IMAGE, description="", depends_on=["a"]),
            TaskStep(id="d", type=TaskType.WRITING, description="", depends_on=["b", "c"]),
        ]
        levels = PipelineExecutor._topological_levels(steps)

        assert len(levels) == 3
        ids_l0 = {s.id for s in levels[0]}
        ids_l1 = {s.id for s in levels[1]}
        assert ids_l0 == {"a"}
        assert ids_l1 == {"b", "c"}
        assert [s.id for s in levels[2]] == ["d"]


class TestBackwardCompatibility:
    """确保旧测试场景仍通过"""

    @pytest.mark.asyncio
    async def test_single_step_success(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        result = await PipelineExecutor().execute(plan)

        assert result.status == "success"
        assert result.success_count == 1

    @pytest.mark.asyncio
    async def test_custom_agent_response(self):
        agent = MockAgent("custom")
        agent.set_response("s1", {"answer": 42})

        plan = _make_plan([("s1", TaskType.CUSTOM)])
        result = await PipelineExecutor(agent_map={"s1": agent}).execute(plan)

        assert result.step_results["s1"].output == {"answer": 42}

    @pytest.mark.asyncio
    async def test_auto_mock_when_no_agent(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        result = await PipelineExecutor().execute(plan)

        assert "auto-mock" in result.step_results["s1"].agent_id

    @pytest.mark.asyncio
    async def test_to_dict(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        result = await PipelineExecutor().execute(plan)
        d = result.to_dict()

        assert "plan_intent" in d
        assert "steps" in d
        assert d["steps"]["s1"]["status"] == "success"