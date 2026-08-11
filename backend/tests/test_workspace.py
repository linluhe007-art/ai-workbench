"""
Phase 3.9.2 测试 — Shared Workspace
覆盖：
- WorkspaceItem 创建与序列化
- InMemoryStorage CRUD
- WorkspaceManager 完整操作
- BaseAgent workspace 集成
- 多 Agent 共享读写
"""

import pytest

from app.workspace.models import WorkspaceItem
from app.workspace.storage import InMemoryStorage
from app.workspace.manager import WorkspaceManager
from app.agents.mock_agent import MockAgent


# ═══════════════════════════════════════════════════════════
# WorkspaceItem 测试
# ═══════════════════════════════════════════════════════════


class TestWorkspaceItem:

    def test_create_with_defaults(self):
        item = WorkspaceItem(
            name="research_result",
            type="dict",
            content={"topics": ["AI"]},
            owner="research-agent",
        )
        assert item.name == "research_result"
        assert item.type == "dict"
        assert item.content == {"topics": ["AI"]}
        assert item.owner == "research-agent"
        assert item.id
        assert item.created_at is not None

    def test_id_is_unique(self):
        a = WorkspaceItem(name="a", type="text", content="x", owner="o")
        b = WorkspaceItem(name="b", type="text", content="y", owner="o")
        assert a.id != b.id

    def test_to_dict(self):
        item = WorkspaceItem(
            name="draft",
            type="text",
            content="Hello",
            owner="writer",
            metadata={"version": 1},
        )
        d = item.to_dict()
        assert d["id"] == item.id
        assert d["name"] == "draft"
        assert d["type"] == "text"
        assert d["content"] == "Hello"
        assert d["owner"] == "writer"
        assert d["metadata"] == {"version": 1}
        assert "created_at" in d


# ═══════════════════════════════════════════════════════════
# InMemoryStorage 测试
# ═══════════════════════════════════════════════════════════


class TestInMemoryStorage:

    def test_create_workspace(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        assert storage.workspace_exists("ws-1")

    def test_create_workspace_idempotent(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        storage.create_workspace("ws-1")
        assert storage.workspace_exists("ws-1")

    def test_add_and_get_item(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        item = WorkspaceItem(name="a", type="text", content="hello", owner="agent-1")
        storage.add_item("ws-1", item)

        got = storage.get_item("ws-1", item.id)
        assert got is not None
        assert got.content == "hello"

    def test_get_nonexistent_item(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        assert storage.get_item("ws-1", "no-such-id") is None

    def test_get_item_wrong_workspace(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        item = WorkspaceItem(name="a", type="text", content="x", owner="o")
        storage.add_item("ws-1", item)
        assert storage.get_item("ws-2", item.id) is None

    def test_list_items(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        for i in range(5):
            storage.add_item("ws-1", WorkspaceItem(
                name=f"item-{i}", type="text", content=f"c-{i}", owner="o",
            ))
        items = storage.list_items("ws-1")
        assert len(items) == 5

    def test_list_empty_workspace(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        assert storage.list_items("ws-1") == []

    def test_list_nonexistent_workspace(self):
        storage = InMemoryStorage()
        assert storage.list_items("ghost") == []

    def test_delete_item(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        item = WorkspaceItem(name="a", type="text", content="x", owner="o")
        storage.add_item("ws-1", item)

        assert storage.delete_item("ws-1", item.id) is True
        assert storage.get_item("ws-1", item.id) is None

    def test_delete_nonexistent_item(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        assert storage.delete_item("ws-1", "nope") is False

    def test_auto_create_workspace_on_add(self):
        storage = InMemoryStorage()
        item = WorkspaceItem(name="a", type="text", content="x", owner="o")
        storage.add_item("auto-ws", item)
        assert storage.workspace_exists("auto-ws")
        assert len(storage.list_items("auto-ws")) == 1

    def test_workspace_isolation(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        storage.create_workspace("ws-2")
        storage.add_item("ws-1", WorkspaceItem(name="a", type="text", content="in-1", owner="o"))
        storage.add_item("ws-2", WorkspaceItem(name="b", type="text", content="in-2", owner="o"))

        assert len(storage.list_items("ws-1")) == 1
        assert len(storage.list_items("ws-2")) == 1
        assert storage.list_items("ws-1")[0].content == "in-1"
        assert storage.list_items("ws-2")[0].content == "in-2"

    def test_clear(self):
        storage = InMemoryStorage()
        storage.create_workspace("ws-1")
        storage.add_item("ws-1", WorkspaceItem(name="a", type="t", content="c", owner="o"))
        storage.clear()
        assert storage.list_items("ws-1") == []


# ═══════════════════════════════════════════════════════════
# WorkspaceManager 测试
# ═══════════════════════════════════════════════════════════


class TestWorkspaceManager:

    def test_create_workspace(self):
        mgr = WorkspaceManager()
        ws_id = mgr.create_workspace("task-123")
        assert ws_id == "task-123"

    def test_add_and_get_item(self):
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        item = WorkspaceItem(name="result", type="dict", content={"score": 9}, owner="agent-1")
        mgr.add_item("ws-1", item)

        got = mgr.get_item("ws-1", item.id)
        assert got is not None
        assert got.content == {"score": 9}

    def test_list_items(self):
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        mgr.add_item("ws-1", WorkspaceItem(name="a", type="t", content="1", owner="o"))
        mgr.add_item("ws-1", WorkspaceItem(name="b", type="t", content="2", owner="o"))

        items = mgr.list_items("ws-1")
        assert len(items) == 2

    def test_delete_item(self):
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        item = WorkspaceItem(name="tmp", type="t", content="x", owner="o")
        mgr.add_item("ws-1", item)

        assert mgr.delete_item("ws-1", item.id) is True
        assert mgr.get_item("ws-1", item.id) is None

    def test_save_artifact(self):
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        item = mgr.save_artifact(
            workspace_id="ws-1",
            owner="research-agent",
            name="news_summary",
            content={"headlines": ["AI News"]},
            item_type="dict",
            metadata={"source": "RSS"},
        )
        assert item.name == "news_summary"
        assert item.owner == "research-agent"
        assert item.type == "dict"
        assert item.metadata == {"source": "RSS"}

    def test_get_artifacts_by_owner(self):
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        mgr.save_artifact("ws-1", "agent-a", "item-1", "content-1")
        mgr.save_artifact("ws-1", "agent-b", "item-2", "content-2")
        mgr.save_artifact("ws-1", "agent-a", "item-3", "content-3")

        a_items = mgr.get_artifacts_by_owner("ws-1", "agent-a")
        assert len(a_items) == 2
        assert all(i.owner == "agent-a" for i in a_items)

    def test_get_artifacts_by_type(self):
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        mgr.save_artifact("ws-1", "o", "a", "text content", item_type="text")
        mgr.save_artifact("ws-1", "o", "b", {"k": "v"}, item_type="dict")
        mgr.save_artifact("ws-1", "o", "c", "more text", item_type="text")

        texts = mgr.get_artifacts_by_type("ws-1", "text")
        assert len(texts) == 2

    def test_save_artifact_defaults(self):
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        item = mgr.save_artifact("ws-1", "agent-1", "simple", "content")

        assert item.type == "text"
        assert item.metadata == {}


# ═══════════════════════════════════════════════════════════
# BaseAgent Workspace 集成测试
# ═══════════════════════════════════════════════════════════


class TestAgentWorkspaceIntegration:

    def test_set_workspace(self):
        agent = MockAgent("a1")
        mgr = WorkspaceManager()
        agent.set_workspace(mgr)
        assert agent.workspace is mgr

    def test_workspace_default_none(self):
        agent = MockAgent("a1")
        assert agent.workspace is None

    @pytest.mark.asyncio
    async def test_save_artifact(self):
        agent = MockAgent("writer")
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        agent.set_workspace(mgr)

        item = await agent.save_artifact("ws-1", "draft", "Hello World", item_type="text")

        assert item.name == "draft"
        assert item.owner == "writer"
        assert item.content == "Hello World"

    @pytest.mark.asyncio
    async def test_get_artifact(self):
        agent = MockAgent("reader")
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        agent.set_workspace(mgr)

        saved = mgr.save_artifact("ws-1", "writer", "note", "important data")
        got = await agent.get_artifact("ws-1", saved.id)

        assert got is not None
        assert got.content == "important data"

    @pytest.mark.asyncio
    async def test_get_artifact_nonexistent(self):
        agent = MockAgent("a1")
        mgr = WorkspaceManager()
        mgr.create_workspace("ws-1")
        agent.set_workspace(mgr)

        got = await agent.get_artifact("ws-1", "no-such-id")
        assert got is None

    @pytest.mark.asyncio
    async def test_save_artifact_without_workspace_raises(self):
        agent = MockAgent("a1")

        with pytest.raises(RuntimeError, match="WorkspaceManager not set"):
            await agent.save_artifact("ws-1", "name", "content")

    @pytest.mark.asyncio
    async def test_get_artifact_without_workspace_raises(self):
        agent = MockAgent("a1")

        with pytest.raises(RuntimeError, match="WorkspaceManager not set"):
            await agent.get_artifact("ws-1", "id")


# ═══════════════════════════════════════════════════════════
# 多 Agent 共享测试
# ═══════════════════════════════════════════════════════════


class TestMultiAgentSharedWorkspace:

    @pytest.mark.asyncio
    async def test_agents_share_workspace(self):
        """多个 Agent 读写同一 workspace"""
        mgr = WorkspaceManager()
        mgr.create_workspace("shared-ws")

        research = MockAgent("research")
        analysis = MockAgent("analysis")
        writing = MockAgent("writing")

        research.set_workspace(mgr)
        analysis.set_workspace(mgr)
        writing.set_workspace(mgr)

        # research 写入
        await research.save_artifact(
            "shared-ws", "raw_news", {"headlines": ["AI breakthrough"]}, item_type="dict",
        )

        # analysis 读取 research 的产物
        research_items = mgr.get_artifacts_by_owner("shared-ws", "research")
        assert len(research_items) == 1
        assert research_items[0].content["headlines"] == ["AI breakthrough"]

        # analysis 写入分析结果
        await analysis.save_artifact(
            "shared-ws", "analysis_report", {"score": 8.5}, item_type="dict",
        )

        # writing 可以看到所有产物
        all_items = mgr.list_items("shared-ws")
        assert len(all_items) == 2
        owners = {i.owner for i in all_items}
        assert owners == {"research", "analysis"}

    @pytest.mark.asyncio
    async def test_workflow_pipeline_sharing(self):
        """模拟完整 pipeline 中的 workspace 共享"""
        mgr = WorkspaceManager()
        task_id = "task-pipeline-001"
        mgr.create_workspace(task_id)

        agents = {
            "research": MockAgent("research"),
            "analysis": MockAgent("analysis"),
            "writing": MockAgent("writing"),
        }
        for agent in agents.values():
            agent.set_workspace(mgr)

        # Step 1: research
        await agents["research"].save_artifact(
            task_id, "research_data", {"items": ["news1", "news2"]}, "dict",
        )

        # Step 2: analysis reads research
        research_artifacts = mgr.get_artifacts_by_owner(task_id, "research")
        assert len(research_artifacts) == 1
        await agents["analysis"].save_artifact(
            task_id, "analysis_result", {"best_topic": "news1", "score": 9}, "dict",
        )

        # Step 3: writing reads analysis
        analysis_artifacts = mgr.get_artifacts_by_owner(task_id, "analysis")
        assert len(analysis_artifacts) == 1
        topic = analysis_artifacts[0].content["best_topic"]
        await agents["writing"].save_artifact(
            task_id, "article", f"# {topic}\n\nThis is the article.", "text",
        )

        # Final: workspace has all 3 artifacts
        all_items = mgr.list_items(task_id)
        assert len(all_items) == 3
        names = {i.name for i in all_items}
        assert names == {"research_data", "analysis_result", "article"}

    @pytest.mark.asyncio
    async def test_different_workspaces_isolated(self):
        """不同 workspace 互相隔离"""
        mgr = WorkspaceManager()
        mgr.create_workspace("task-A")
        mgr.create_workspace("task-B")

        agent_a = MockAgent("agent-a")
        agent_b = MockAgent("agent-b")
        agent_a.set_workspace(mgr)
        agent_b.set_workspace(mgr)

        await agent_a.save_artifact("task-A", "data", "A's data")
        await agent_b.save_artifact("task-B", "data", "B's data")

        a_items = mgr.list_items("task-A")
        b_items = mgr.list_items("task-B")

        assert len(a_items) == 1 and a_items[0].content == "A's data"
        assert len(b_items) == 1 and b_items[0].content == "B's data"