"""Phase 5.11 tests - Replay System"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.intelligence.context.snapshot import ContextSnapshot, SnapshotStore, get_snapshot_store
from app.replay.replayer import Replayer, ReplayResult, get_replayer
from app.main import app


class TestContextSnapshot:
    def test_default(self):
        s = ContextSnapshot()
        assert s.id != ""
        assert s.task_id == ""

    def test_to_dict(self):
        s = ContextSnapshot(
            task_id="t1", user_input="research AI",
            memory_context={"key": "val"},
            plan={"steps": 3},
            agent="research-agent",
            prompt="Research {{topic}}",
            model="llama3",
            result={"output": "done"},
        )
        d = s.to_dict()
        assert d["task_id"] == "t1"
        assert d["user_input"] == "research AI"
        assert d["memory_context"]["key"] == "val"
        assert d["plan"]["steps"] == 3
        assert d["agent"] == "research-agent"

    def test_created_at_iso(self):
        s = ContextSnapshot()
        assert "T" in s.created_at


class TestSnapshotStore:
    def test_save_and_get(self):
        store = SnapshotStore()
        snap = ContextSnapshot(task_id="t1", user_input="test")
        store.save(snap)
        retrieved = store.get("t1")
        assert retrieved is not None
        assert retrieved.user_input == "test"

    def test_get_nonexistent(self):
        store = SnapshotStore()
        assert store.get("nonexistent") is None

    def test_delete(self):
        store = SnapshotStore()
        store.save(ContextSnapshot(task_id="t1"))
        assert store.delete("t1") is True
        assert store.get("t1") is None

    def test_delete_nonexistent(self):
        store = SnapshotStore()
        assert store.delete("nonexistent") is False

    def test_list_task_ids(self):
        store = SnapshotStore()
        store.save(ContextSnapshot(task_id="t1"))
        store.save(ContextSnapshot(task_id="t2"))
        ids = store.list_task_ids()
        assert "t1" in ids
        assert "t2" in ids

    def test_overwrite(self):
        store = SnapshotStore()
        store.save(ContextSnapshot(task_id="t1", user_input="old"))
        store.save(ContextSnapshot(task_id="t1", user_input="new"))
        snap = store.get("t1")
        assert snap.user_input == "new"

    def test_singleton(self):
        s1 = get_snapshot_store()
        s2 = get_snapshot_store()
        assert s1 is s2


class TestReplayResult:
    def test_default(self):
        r = ReplayResult()
        assert r.success is False

    def test_to_dict(self):
        r = ReplayResult(task_id="t1", success=True, replayed_steps=["memory", "plan"])
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["success"] is True
        assert len(d["replayed_steps"]) == 2

class TestReplayer:
    @pytest.mark.asyncio
    async def test_replay_nonexistent(self):
        r = Replayer()
        result = await r.replay("nonexistent")
        assert result.success is False
        assert "No snapshot" in result.error

    @pytest.mark.asyncio
    async def test_replay_with_snapshot(self):
        store = get_snapshot_store()
        snap = ContextSnapshot(
            task_id="replay-test-1", user_input="test",
            memory_context={"key": "val"},
            plan={"steps": 2},
            agent="agent-1",
            prompt="test prompt",
            model="llama3",
            result={"output": "done"},
        )
        store.save(snap)

        r = Replayer()
        result = await r.replay("replay-test-1")
        assert result.success is True
        assert "memory_loaded" in result.replayed_steps
        assert "plan_loaded" in result.replayed_steps
        assert "agent_loaded" in result.replayed_steps
        assert "prompt_loaded" in result.replayed_steps
        assert "model_loaded" in result.replayed_steps

    @pytest.mark.asyncio
    async def test_replay_partial_snapshot(self):
        store = get_snapshot_store()
        snap = ContextSnapshot(task_id="partial-1", user_input="test")
        store.save(snap)
        r = Replayer()
        result = await r.replay("partial-1")
        assert result.success is True
        assert len(result.replayed_steps) == 0

    def test_singleton(self):
        r1 = get_replayer()
        r2 = get_replayer()
        assert r1 is r2


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestReplayAPI:
    @pytest.mark.asyncio
    async def test_get_context_nonexistent(self, client):
        resp = await client.get("/api/v1/tasks/nonexistent/context")
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_get_context_with_data(self, client):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="ctx-test", user_input="hi"))
        resp = await client.get("/api/v1/tasks/ctx-test/context")
        data = resp.json()
        assert data["success"] is True
        assert "context" in data

    @pytest.mark.asyncio
    async def test_replay_endpoint(self, client):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="replay-api", user_input="test"))
        resp = await client.post("/api/v1/tasks/replay-api/replay")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_replay_nonexistent_endpoint(self, client):
        resp = await client.post("/api/v1/tasks/nonexistent/replay")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_replay_result_structure(self, client):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="replay-struct", user_input="test"))
        resp = await client.post("/api/v1/tasks/replay-struct/replay")
        data = resp.json()
        assert "result" in data
        assert "replayed_steps" in data["result"]

class TestReplayExtra:
    def test_snapshot_with_all_fields_populated(self):
        s = ContextSnapshot(
            task_id="full", user_input="hi", memory_context={"a": 1},
            knowledge_context={"b": 2}, plan={"c": 3}, agent="x",
            prompt="pro", model="m1", result={"out": "yes"},
        )
        d = s.to_dict()
        assert d["task_id"] == "full"
        assert d["memory_context"]["a"] == 1
        assert d["knowledge_context"]["b"] == 2

    @pytest.mark.asyncio
    async def test_replay_with_plan_only(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="plan-only", plan={"steps": 5}))
        r = get_replayer()
        result = await r.replay("plan-only")
        assert "plan_loaded" in result.replayed_steps

    @pytest.mark.asyncio
    async def test_replay_with_agent_only(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="agent-only", agent="researcher"))
        r = get_replayer()
        result = await r.replay("agent-only")
        assert "agent_loaded" in result.replayed_steps

    @pytest.mark.asyncio
    async def test_replay_output_preserved(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="out-test", result={"final": "done"}))
        r = get_replayer()
        result = await r.replay("out-test")
        assert result.output["final"] == "done"

    def test_snapshot_store_empty(self):
        store = SnapshotStore()
        assert store.list_task_ids() == []

    @pytest.mark.asyncio
    async def test_snapshot_delete_then_get(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="del-test"))
        store.delete("del-test")
        assert store.get("del-test") is None

    @pytest.mark.asyncio
    async def test_api_context_200(self, client):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="api-ctx-200", user_input="ok"))
        resp = await client.get("/api/v1/tasks/api-ctx-200/context")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_replay_200(self, client):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="api-replay-200"))
        resp = await client.post("/api/v1/tasks/api-replay-200/replay")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_snapshot_multiple_tasks_isolation(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="iso-1", user_input="data1"))
        store.save(ContextSnapshot(task_id="iso-2", user_input="data2"))
        assert store.get("iso-1").user_input == "data1"
        assert store.get("iso-2").user_input == "data2"
