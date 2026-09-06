"""
Phase 5.3 tests - MemoryIntegration (Planner/Agent auto-read).
"""
import pytest
from app.memory.manager import MemoryManager, MemoryType, reset_memory_manager
from app.memory.integration import MemoryIntegration, get_memory_integration, reset_memory_integration


@pytest.fixture(autouse=True)
def _reset():
    reset_memory_manager()
    reset_memory_integration()
    yield
    reset_memory_manager()
    reset_memory_integration()


class TestMemoryIntegration:
    def test_get_context_for_task(self):
        mgr = MemoryManager()
        mgr.save_memory("User: John, role: developer", memory_type="profile", importance=0.9)
        mgr.save_memory("Prefer dark mode and markdown", memory_type="preference", importance=0.7)
        mgr.save_memory("Python async programming patterns", memory_type="knowledge", tags=["python", "async"])
        mgr.save_memory("Previous task: built async API", memory_type="experience", tags=["python", "success"])

        integration = MemoryIntegration(mgr)
        ctx = integration.get_context_for_task("build an async service")

        assert len(ctx["profile"]) == 1
        assert len(ctx["preferences"]) == 1
        assert len(ctx["relevant_knowledge"]) >= 1
        assert len(ctx["past_experiences"]) >= 1

    def test_context_empty_when_no_memory(self):
        mgr = MemoryManager()
        integration = MemoryIntegration(mgr)
        ctx = integration.get_context_for_task("some task")
        assert ctx["profile"] == []
        assert ctx["preferences"] == []
        assert ctx["relevant_knowledge"] == []
        assert ctx["past_experiences"] == []

    def test_build_prompt_context(self):
        mgr = MemoryManager()
        mgr.save_memory("Name: Alice", memory_type="profile", importance=0.9)
        integration = MemoryIntegration(mgr)
        prompt = integration.build_prompt_context("task")
        assert "Alice" in prompt
        assert "User Profile" in prompt

    def test_build_prompt_empty(self):
        mgr = MemoryManager()
        integration = MemoryIntegration(mgr)
        prompt = integration.build_prompt_context("task")
        assert prompt == ""

    def test_record_task_memory_success(self):
        mgr = MemoryManager()
        integration = MemoryIntegration(mgr)
        integration.record_task_memory(
            "test task",
            {"agents": ["researcher"], "duration_ms": 500},
            success=True,
        )
        exps = mgr.get_experiences()
        assert len(exps) == 1
        assert "success" in exps[0]["tags"]
        assert "True" in exps[0]["content"]

    def test_record_task_memory_failure(self):
        mgr = MemoryManager()
        integration = MemoryIntegration(mgr)
        integration.record_task_memory(
            "failed task",
            {"agents": ["writer"], "error": "timeout"},
            success=False,
        )
        exps = mgr.get_experiences()
        assert len(exps) == 1
        assert "failure" in exps[0]["tags"]

    def test_record_user_input(self):
        mgr = MemoryManager()
        integration = MemoryIntegration(mgr)
        mid = integration.record_user_input("user said hello", memory_type="knowledge")
        assert mid
        record = mgr.get_memory(mid)
        assert record["content"] == "user said hello"
        assert "user-input" in record["tags"]

    def test_content_filtered_by_task_query(self):
        mgr = MemoryManager()
        mgr.save_memory("Python async guides", memory_type="knowledge", tags=["python"])
        mgr.save_memory("Cooking recipes", memory_type="knowledge", tags=["cooking"])
        integration = MemoryIntegration(mgr)
        ctx = integration.get_context_for_task("python project")
        contents = [k["content"] for k in ctx["relevant_knowledge"]]
        assert any("Python" in c or "python" in c for c in contents)

    def test_experiences_flattened_to_content(self):
        mgr = MemoryManager()
        mgr.save_memory("Learned about async patterns", memory_type="experience", tags=["learning"])
        integration = MemoryIntegration(mgr)
        ctx = integration.get_context_for_task("async patterns")
        assert len(ctx["past_experiences"]) == 1

    def test_not_found_task_returns_empty(self):
        mgr = MemoryManager()
        mgr.save_memory("unrelated", memory_type="knowledge")
        integration = MemoryIntegration(mgr)
        ctx = integration.get_context_for_task("completely different topic")
        assert ctx["relevant_knowledge"] == []


class TestMemoryIntegrationSingleton:
    def test_get_returns_same(self):
        reset_memory_integration()
        i1 = get_memory_integration()
        i2 = get_memory_integration()
        assert i1 is i2

    def test_reset_creates_new(self):
        reset_memory_integration()
        i1 = get_memory_integration()
        reset_memory_integration()
        i2 = get_memory_integration()
        assert i1 is not i2
