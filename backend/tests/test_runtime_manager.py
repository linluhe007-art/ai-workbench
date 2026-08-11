"""
Phase 4.1 测试 — AppRuntime Manager
覆盖：
- 初始化
- 创建任务
- 获取 Agent
- 获取指标
- 获取 Trace
- 单例重置
"""

import pytest

from app.runtime.manager import AppRuntime, get_runtime, reset_runtime, TaskStatus


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    yield
    reset_runtime()


class TestAppRuntime:
    def test_init_creates_agents(self):
        rt = AppRuntime()
        agents = rt.get_agents()
        assert len(agents) >= 1
        ids = [a["id"] for a in agents]
        assert "default" in ids

    def test_init_creates_components(self):
        rt = AppRuntime()
        assert rt.trace_collector is not None
        assert rt.experience is not None
        assert rt.history is not None
        assert rt.runtime is not None
        assert rt.planner is not None
        assert rt.executor is not None

    def test_create_task(self):
        rt = AppRuntime()
        record = rt.create_task("test task")
        assert record.task_id.startswith("task-")
        assert record.task == "test task"
        assert record.status == TaskStatus.PENDING

    def test_get_task(self):
        rt = AppRuntime()
        record = rt.create_task("test")
        found = rt.get_task(record.task_id)
        assert found is not None
        assert found.task_id == record.task_id

    def test_get_task_not_found(self):
        rt = AppRuntime()
        assert rt.get_task("nonexist") is None

    def test_list_tasks(self):
        rt = AppRuntime()
        rt.create_task("t1")
        rt.create_task("t2")
        tasks = rt.list_tasks()
        assert len(tasks) == 2

    def test_get_agents(self):
        rt = AppRuntime()
        agents = rt.get_agents()
        assert isinstance(agents, list)

    def test_get_metrics(self):
        rt = AppRuntime()
        metrics = rt.get_metrics()
        assert "total_tasks" in metrics
        assert "success_rate" in metrics

    def test_get_trace(self):
        rt = AppRuntime()
        trace = rt.get_trace("any-task")
        assert isinstance(trace, list)

    def test_get_history(self):
        rt = AppRuntime()
        history = rt.get_history("any-task")
        assert isinstance(history, list)

    def test_singleton(self):
        rt1 = get_runtime()
        rt2 = get_runtime()
        assert rt1 is rt2

    def test_reset(self):
        rt1 = get_runtime()
        reset_runtime()
        rt2 = get_runtime()
        assert rt1 is not rt2

    async def test_run_task(self):
        rt = AppRuntime()
        record = rt.create_task("搜索资料")
        result = await rt.run_task(record.task_id, max_iterations=1)
        assert result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
        assert result.loop_result is not None

    async def test_run_task_not_found(self):
        rt = AppRuntime()
        with pytest.raises(ValueError, match="Task not found"):
            await rt.run_task("nonexist")

    def test_task_to_dict(self):
        rt = AppRuntime()
        record = rt.create_task("test")
        d = record.to_dict()
        assert "task_id" in d
        assert "status" in d
        assert "created_at" in d