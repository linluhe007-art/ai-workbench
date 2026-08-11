"""
Phase 3.14 测试 — AgentMemory
覆盖：
- remember / recall
- 事件类型过滤
- 关键词查询
- 最近事件
- 计数
- 上限淘汰
"""

import pytest
from app.memory.agent_memory import AgentMemory


class TestAgentMemoryRemember:

    def test_remember(self):
        mem = AgentMemory("agent-1")
        event = mem.remember("task_complete", {"task": "研究AI"})
        assert event.event_type == "task_complete"
        assert event.content == {"task": "研究AI"}

    def test_remember_with_metadata(self):
        mem = AgentMemory("agent-1")
        event = mem.remember("error", "timeout", {"step": "research"})
        assert event.metadata == {"step": "research"}

    def test_total_events(self):
        mem = AgentMemory("agent-1")
        mem.remember("a", "1")
        mem.remember("b", "2")
        assert mem.total_events == 2

    def test_agent_id(self):
        mem = AgentMemory("my-agent")
        assert mem.agent_id == "my-agent"

    def test_clear(self):
        mem = AgentMemory("agent-1")
        mem.remember("a", "1")
        mem.clear()
        assert mem.total_events == 0


class TestAgentMemoryRecall:

    def test_recall_all(self):
        mem = AgentMemory("agent-1")
        mem.remember("task", "研究AI")
        mem.remember("task", "写报告")
        results = mem.recall()
        assert len(results) == 2

    def test_recall_by_type(self):
        mem = AgentMemory("agent-1")
        mem.remember("task_complete", "done")
        mem.remember("error", "fail")
        mem.remember("task_complete", "done2")
        results = mem.recall(event_type="task_complete")
        assert len(results) == 2

    def test_recall_by_query(self):
        mem = AgentMemory("agent-1")
        mem.remember("task", "研究AI趋势")
        mem.remember("task", "写技术报告")
        results = mem.recall(query="研究")
        assert len(results) == 1
        assert "研究" in str(results[0]["content"])

    def test_recall_by_type_and_query(self):
        mem = AgentMemory("agent-1")
        mem.remember("task", "研究AI")
        mem.remember("error", "研究超时")
        results = mem.recall(query="研究", event_type="error")
        assert len(results) == 1

    def test_recall_empty(self):
        mem = AgentMemory("agent-1")
        results = mem.recall()
        assert len(results) == 0

    def test_recall_no_match(self):
        mem = AgentMemory("agent-1")
        mem.remember("task", "研究AI")
        results = mem.recall(query="烹饪")
        assert len(results) == 0

    def test_recall_recent_first(self):
        mem = AgentMemory("agent-1")
        mem.remember("task", "first")
        mem.remember("task", "second")
        mem.remember("task", "third")
        results = mem.recall(limit=2)
        assert results[0]["content"] == "third"
        assert results[1]["content"] == "second"

    def test_recall_limit(self):
        mem = AgentMemory("agent-1")
        for i in range(20):
            mem.remember("task", f"event-{i}")
        results = mem.recall(limit=5)
        assert len(results) == 5

    def test_result_fields(self):
        mem = AgentMemory("agent-1")
        mem.remember("task", "content", {"key": "val"})
        results = mem.recall()
        r = results[0]
        assert "event_type" in r
        assert "content" in r
        assert "metadata" in r
        assert "created_at" in r


class TestAgentMemoryHelpers:

    def test_get_recent(self):
        mem = AgentMemory("agent-1")
        for i in range(5):
            mem.remember("task", f"event-{i}")
        recent = mem.get_recent(3)
        assert len(recent) == 3
        assert recent[0]["content"] == "event-4"

    def test_count_by_type(self):
        mem = AgentMemory("agent-1")
        mem.remember("task", "a")
        mem.remember("error", "b")
        mem.remember("task", "c")
        assert mem.count_by_type("task") == 2
        assert mem.count_by_type("error") == 1

    def test_max_events_eviction(self):
        mem = AgentMemory("agent-1", max_events=5)
        for i in range(10):
            mem.remember("task", f"event-{i}")
        assert mem.total_events == 5
        # 最新的 5 条保留
        recent = mem.get_recent(1)
        assert recent[0]["content"] == "event-9"

    def test_metadata_query(self):
        mem = AgentMemory("agent-1")
        mem.remember("task", {"result": "ok"}, {"agent": "researcher"})
        results = mem.recall(query="researcher")
        assert len(results) == 1