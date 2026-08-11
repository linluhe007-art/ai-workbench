"""
Phase 3.15 测试 — PipelineExecutor 经验写回
覆盖：
- 成功执行自动记录
- 失败执行自动记录
- metadata 包含 duration 和 failed_steps
- 无 experience 时不报错
- agents 收集正确
"""

import pytest
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.orchestrator.planner import TaskPlan, TaskStep, TaskType
from app.orchestrator.executor import StepStatus
from app.agents.mock_agent import MockAgent
from app.memory.experience import ExperienceMemory


def _make_plan(steps: list[tuple]) -> TaskPlan:
    task_steps = []
    for item in steps:
        sid, stype = item[0], item[1]
        deps = item[2] if len(item) > 2 else []
        task_steps.append(TaskStep(
            id=sid, type=stype, description=f"desc-{sid}", depends_on=deps,
        ))
    return TaskPlan(intent="test writeback", steps=task_steps)


def _failing_agent(agent_id: str) -> MockAgent:
    class _Fail(MockAgent):
        async def execute_step(self, step, context=None):
            self._call_log.append({"step_id": step.id, "task_type": step.type.value, "description": step.description})
            raise RuntimeError("timeout")
    return _Fail(agent_id)


class TestExperienceWriteback:

    @pytest.mark.asyncio
    async def test_success_records_experience(self):
        exp = ExperienceMemory()
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor(experience=exp)
        await executor.execute(plan)

        assert exp.total_records == 1
        records = exp.query_experience("test writeback")
        assert len(records) == 1
        assert records[0]["success"] is True

    @pytest.mark.asyncio
    async def test_failure_records_experience(self):
        exp = ExperienceMemory()
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(
            agent_map={"s1": _failing_agent("fail")},
            experience=exp,
        )
        await executor.execute(plan)

        assert exp.total_records == 1
        records = exp.query_experience("test writeback")
        assert records[0]["success"] is False

    @pytest.mark.asyncio
    async def test_metadata_contains_duration(self):
        exp = ExperienceMemory()
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor(experience=exp)
        await executor.execute(plan)

        records = exp.query_experience("test writeback")
        assert "duration_ms" in records[0]["metadata"]
        assert records[0]["metadata"]["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_metadata_contains_failed_steps(self):
        exp = ExperienceMemory()
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(
            agent_map={"s1": _failing_agent("fail")},
            experience=exp,
        )
        await executor.execute(plan)

        records = exp.query_experience("test writeback")
        assert "s1" in records[0]["metadata"]["failed_steps"]

    @pytest.mark.asyncio
    async def test_agents_collected(self):
        exp = ExperienceMemory()
        agent = MockAgent("my-agent")
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor(
            agent_map={"s1": agent},
            experience=exp,
        )
        await executor.execute(plan)

        records = exp.query_experience("test writeback")
        assert "my-agent" in records[0]["agents"]

    @pytest.mark.asyncio
    async def test_no_experience_no_error(self):
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor(experience=None)
        result = await executor.execute(plan)
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_multi_step_records_once(self):
        exp = ExperienceMemory()
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("writing", TaskType.WRITING, ["research"]),
        ])
        executor = PipelineExecutor(experience=exp)
        await executor.execute(plan)

        assert exp.total_records == 1
        records = exp.query_experience("test writeback")
        assert records[0]["metadata"]["step_count"] == 2

    @pytest.mark.asyncio
    async def test_partial_failure_records(self):
        exp = ExperienceMemory()

        class _FailOnWriting(MockAgent):
            async def execute_step(self, step, context=None):
                self._call_log.append({"step_id": step.id, "task_type": step.type.value, "description": step.description})
                if step.id == "writing":
                    raise RuntimeError("boom")
                return self._build_output(step)

        agent = _FailOnWriting("agent")
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("writing", TaskType.WRITING, ["research"]),
        ])
        executor = PipelineExecutor(agent_map={"research": agent, "writing": agent}, experience=exp)
        await executor.execute(plan)

        records = exp.query_experience("test writeback")
        assert records[0]["success"] is False
        assert "writing" in records[0]["metadata"]["failed_steps"]

class TestExperienceWritebackEdgeCases:

    @pytest.mark.asyncio
    async def test_skipped_steps_in_metadata(self):
        exp = ExperienceMemory()

        class _FailResearch(MockAgent):
            async def execute_step(self, step, context=None):
                self._call_log.append({"step_id": step.id, "task_type": step.type.value, "description": step.description})
                if step.id == "research":
                    raise RuntimeError("timeout")
                return self._build_output(step)

        agent = _FailResearch("agent")
        plan = _make_plan([
            ("research", TaskType.RESEARCH),
            ("writing", TaskType.WRITING, ["research"]),
        ])
        executor = PipelineExecutor(agent_map={"research": agent, "writing": agent}, experience=exp)
        await executor.execute(plan)

        records = exp.query_experience("test writeback")
        assert records[0]["success"] is False

    @pytest.mark.asyncio
    async def test_experience_query_returns_recent_first(self):
        exp = ExperienceMemory()
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor(experience=exp)

        await executor.execute(plan)
        await executor.execute(plan)

        assert exp.total_records == 2

    @pytest.mark.asyncio
    async def test_experience_preserves_intent(self):
        exp = ExperienceMemory()
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor(experience=exp)
        await executor.execute(plan)

        records = exp.query_experience("test writeback")
        assert records[0]["task_pattern"] == "test writeback"

    @pytest.mark.asyncio
    async def test_auto_mock_agent_recorded(self):
        exp = ExperienceMemory()
        plan = _make_plan([("s1", TaskType.CHAT)])
        executor = PipelineExecutor(experience=exp)
        await executor.execute(plan)

        records = exp.query_experience("test writeback")
        assert len(records[0]["agents"]) >= 1

    @pytest.mark.asyncio
    async def test_experience_with_recovery_flow(self):
        exp = ExperienceMemory()
        agent = _failing_agent("fail")
        plan = _make_plan([("s1", TaskType.CUSTOM)])
        executor = PipelineExecutor(agent_map={"s1": agent}, experience=exp)
        result = await executor.execute_with_recovery(plan, max_retries=0)

        assert result.status == "failed"
        assert exp.total_records >= 1