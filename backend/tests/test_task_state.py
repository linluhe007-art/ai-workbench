"""
TaskState 测试
覆盖：状态转换、TaskRecord 生命周期、TaskStateStore。
"""

from app.orchestrator.task_state import TaskRecord, TaskStateStore, TaskStatus


class TestTaskRecord:

    def test_create_record(self):
        record = TaskRecord(intent="测试任务")
        assert record.status == TaskStatus.PENDING
        assert record.task_id
        assert record.intent == "测试任务"

    def test_status_transition(self):
        record = TaskRecord(intent="test")
        record.update_status(TaskStatus.RUNNING)
        assert record.status == TaskStatus.RUNNING
        record.update_status(TaskStatus.COMPLETED)
        assert record.status == TaskStatus.COMPLETED

    def test_mark_step_done(self):
        record = TaskRecord(intent="test", steps_total=3)
        record.mark_step_done()
        assert record.steps_completed == 1
        record.mark_step_done()
        assert record.steps_completed == 2

    def test_to_dict(self):
        record = TaskRecord(intent="test")
        d = record.to_dict()
        assert "task_id" in d
        assert "status" in d
        assert "created_at" in d


class TestTaskStateStore:

    def test_create_and_get(self):
        store = TaskStateStore()
        record = store.create("写文章", steps_total=5)
        assert record.intent == "写文章"
        found = store.get(record.task_id)
        assert found is record

    def test_update_status(self):
        store = TaskStateStore()
        record = store.create("test")
        store.update(record.task_id, TaskStatus.RUNNING)
        assert store.get(record.task_id).status == TaskStatus.RUNNING

    def test_list_all(self):
        store = TaskStateStore()
        store.create("task1")
        store.create("task2")
        store.create("task3")
        assert len(store.list_all()) == 3

    def test_list_by_status(self):
        store = TaskStateStore()
        r1 = store.create("task1")
        r2 = store.create("task2")
        store.update(r1.task_id, TaskStatus.COMPLETED)
        completed = store.list_all(TaskStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].task_id == r1.task_id

    def test_get_nonexistent(self):
        store = TaskStateStore()
        assert store.get("nonexistent") is None