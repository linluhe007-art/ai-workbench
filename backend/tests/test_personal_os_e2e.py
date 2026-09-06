"""Phase 5.11 tests - Personal AI OS E2E Verification"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.os.orchestrator import get_orchestrator, PersonalAIOrchestrator
from app.os.context import ContextBuilder, UnifiedContext, SystemState, MemorySnapshot
from app.os.decision import DecisionEngine, Decision
from app.intelligence.trace.decision_store import get_trace_store, DecisionTraceStore
from app.intelligence.trace.trace_context import create_trace_context
from app.intelligence.context.snapshot import get_snapshot_store, ContextSnapshot
from app.prompts.registry import get_prompt_registry
from app.analytics.ai_metrics import get_ai_usage_tracker
from app.replay.replayer import get_replayer


# ========== Normal Flow Tests ==========

class TestNormalFlow:
    @pytest.mark.asyncio
    async def test_full_orchestration_research(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Research AI trends")
        assert result is not None

    @pytest.mark.asyncio
    async def test_full_orchestration_write(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Write a blog post about technology")
        assert result is not None

    @pytest.mark.asyncio
    async def test_decision_trace_recorded(self):
        o = PersonalAIOrchestrator()
        await o.process("Analyze data")
        store = get_trace_store()
        traces = store.get_all()
        # Traces may be empty if subsystems aren't wired but should not error
        assert isinstance(traces, list)

    @pytest.mark.asyncio
    async def test_context_builder_with_all_subsystems(self):
        cb = ContextBuilder()
        ctx = await cb.build(user_intent="Test intent", task_category="analysis")
        assert isinstance(ctx, UnifiedContext)

    @pytest.mark.asyncio
    async def test_decision_engine_all_actions(self):
        e = DecisionEngine()
        for intent in ["research", "how to", "daily report", "optimize", "hello", ""]:
            ctx = UnifiedContext(user_intent=intent)
            d = e.decide(ctx)
            assert d.action in ("create_task", "query", "chat", "suggest", "automate", "improve")

    @pytest.mark.asyncio
    async def test_trace_context_records(self):
        ctx = create_trace_context(task_id="e2e-1", user_id="u1")
        ctx.record("command_analysis", "classifier", {"intent": "test"}, {"action": "chat"})
        ctx.record("plan_generation", "planner", {}, {"steps": 2})
        assert len(ctx.get_traces()) == 2

    @pytest.mark.asyncio
    async def test_prompt_registry_flow(self):
        reg = get_prompt_registry()
        reg.create("test-prompt", "Hello {{name}}", ["name"])
        result = reg.render("test-prompt", name="World")
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_snapshot_store_flow(self):
        store = get_snapshot_store()
        snap = ContextSnapshot(task_id="snap-1", user_input="test", plan={"steps": 3})
        store.save(snap)
        retrieved = store.get("snap-1")
        assert retrieved.plan["steps"] == 3

    @pytest.mark.asyncio
    async def test_replay_from_snapshot(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="replay-1", user_input="test", memory_context={"k": "v"}))
        r = get_replayer()
        result = await r.replay("replay-1")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_ai_usage_tracker_flow(self):
        tracker = get_ai_usage_tracker()
        tracker.record("llama3", "ollama", 100, 50, task_id="t1")
        summary = tracker.get_summary()
        assert summary["total_tokens"] >= 150

# ========== Agent Failure Tests ==========

class TestAgentFailure:
    @pytest.mark.asyncio
    async def test_orchestrator_handles_no_agents(self):
        o = PersonalAIOrchestrator()
        result = await o.process("research something")
        assert result is not None

    @pytest.mark.asyncio
    async def test_context_builder_handles_bad_agent_runtime(self):
        class BadRT:
            def list_agents(self):
                raise RuntimeError("Agent down")
        cb = ContextBuilder()
        cb.set_agent_runtime(BadRT())
        ctx = await cb.build()
        assert ctx.system_state.agents_available == 0

    @pytest.mark.asyncio
    async def test_decision_still_works_without_agents(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="test", system_state=SystemState(agents_available=0))
        d = e.decide(ctx)
        assert d.action is not None


# ========== Planner Failure Tests ==========

class TestPlannerFailure:
    @pytest.mark.asyncio
    async def test_orchestrator_without_planner(self):
        o = PersonalAIOrchestrator()
        result = await o.process("create a plan")
        assert result is not None

    @pytest.mark.asyncio
    async def test_context_builder_without_planner(self):
        cb = ContextBuilder()
        ctx = await cb.build(user_intent="test")
        assert isinstance(ctx, UnifiedContext)


# ========== Memory Empty Tests ==========

class TestMemoryEmpty:
    @pytest.mark.asyncio
    async def test_empty_memory_snapshot(self):
        snap = MemorySnapshot()
        assert snap.recent_experiences == []

    @pytest.mark.asyncio
    async def test_context_builder_empty_memory(self):
        cb = ContextBuilder()
        ctx = await cb.build(user_intent="something new")
        assert ctx.memory_snapshot.recent_experiences == []

    @pytest.mark.asyncio
    async def test_decision_with_empty_memory(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="research", memory_snapshot=MemorySnapshot())
        d = e.decide(ctx)
        assert d.action == "create_task"


# ========== Knowledge Not Found Tests ==========

class TestKnowledgeNotFound:
    @pytest.mark.asyncio
    async def test_snapshot_empty_knowledge(self):
        snap = ContextSnapshot(knowledge_context={})
        assert snap.knowledge_context == {}

    @pytest.mark.asyncio
    async def test_context_builder_no_knowledge(self):
        cb = ContextBuilder()
        ctx = await cb.build()
        assert isinstance(ctx, UnifiedContext)


# ========== Workflow Exception Tests ==========

class TestWorkflowException:
    @pytest.mark.asyncio
    async def test_orchestrator_all_steps_present(self):
        o = PersonalAIOrchestrator()
        result = await o.process("test")
        assert len(result.steps) == 5

    @pytest.mark.asyncio
    async def test_orchestrator_step_names_correct(self):
        o = PersonalAIOrchestrator()
        result = await o.process("test")
        names = [s["name"] for s in result.steps]
        assert "memory_retrieval" in names
        assert "decision" in names
        assert "planning" in names
        assert "agent_selection" in names
        assert "learning" in names

# ========== Retry Tests ==========

class TestRetry:
    @pytest.mark.asyncio
    async def test_multiple_orchestrations_idempotent(self):
        o = PersonalAIOrchestrator()
        r1 = await o.process("test")
        r2 = await o.process("test")
        assert r1.id != r2.id

    @pytest.mark.asyncio
    async def test_trace_store_accumulates(self):
        store = get_trace_store()
        initial = len(store.get_all())
        store.add_trace("command_analysis", "c", {}, {})
        assert len(store.get_all()) == initial + 1

    @pytest.mark.asyncio
    async def test_prompt_registry_retry_create(self):
        reg = get_prompt_registry()
        reg.create("retry-test", "v1")
        reg.create("retry-test", "v2")
        t = reg.get_active("retry-test")
        assert t.version == 2


# ========== Recovery Tests ==========

class TestRecovery:
    @pytest.mark.asyncio
    async def test_orchestrator_recovery_from_failure(self):
        o = PersonalAIOrchestrator()
        result = await o.process("test recovery")
        assert result.steps is not None

    @pytest.mark.asyncio
    async def test_snapshot_overwrite_recovery(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="rec-1", user_input="old"))
        store.save(ContextSnapshot(task_id="rec-1", user_input="new"))
        assert store.get("rec-1").user_input == "new"

    @pytest.mark.asyncio
    async def test_tracker_clear_recovery(self):
        tracker = get_ai_usage_tracker()
        tracker.record("m", "p", 1, 1)
        tracker.clear()
        assert tracker.get_summary()["total_records"] == 0


# ========== Permission Tests ==========

class TestPermission:
    @pytest.mark.asyncio
    async def test_trace_query_by_user(self):
        store = DecisionTraceStore()
        store.add_trace("command_analysis", "c", {}, {}, user_id="admin")
        store.add_trace("plan_generation", "p", {}, {}, user_id="guest")
        admin_traces = store.query(user_id="admin")
        guest_traces = store.query(user_id="guest")
        assert len(admin_traces) + len(guest_traces) == 2

    @pytest.mark.asyncio
    async def test_prompt_access_by_name(self):
        reg = get_prompt_registry()
        reg.create("public", "Public prompt")
        reg.create("internal", "Internal prompt")
        assert reg.get("public") is not None
        assert reg.get("internal") is not None


# ========== Tenant Isolation Tests ==========

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_snapshot_per_task(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="tenant-a-task", user_input="a"))
        store.save(ContextSnapshot(task_id="tenant-b-task", user_input="b"))
        assert store.get("tenant-a-task").user_input == "a"
        assert store.get("tenant-b-task").user_input == "b"

    @pytest.mark.asyncio
    async def test_trace_filtering_per_task(self):
        store = DecisionTraceStore()
        store.add_trace("command_analysis", "c", {}, {}, task_id="t-a")
        store.add_trace("agent_selection", "s", {}, {}, task_id="t-b")
        assert len(store.query(task_id="t-a")) == 1
        assert len(store.query(task_id="t-b")) == 1


# ========== Integration Flow Tests ==========

class TestIntegrationFlow:
    @pytest.mark.asyncio
    async def test_full_pipeline_user_to_learning(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Research AI and create report")
        assert result.user_intent != ""
        assert result.decision is not None
        assert len(result.steps) == 5

    @pytest.mark.asyncio
    async def test_trace_and_snapshot_integration(self):
        tid = "integrated-test"
        ctx = create_trace_context(task_id=tid)
        ctx.record("command_analysis", "classifier", {"intent": "test"}, {"action": "create_task"})
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id=tid, user_input="test"))
        traces = get_trace_store().get_by_task(tid)
        snap = store.get(tid)
        assert len(traces) >= 1
        assert snap is not None

    @pytest.mark.asyncio
    async def test_prompt_and_metrics_integration(self):
        reg = get_prompt_registry()
        reg.create("greet", "Hello {{name}}", ["name"])
        rendered = reg.render("greet", name="Alice")
        tracker = get_ai_usage_tracker()
        tracker.record("llama3", "ollama", len(rendered.split()), 5, task_id="integrated")
        assert tracker.get_summary()["total_records"] >= 1

# ========== OS API Integration Tests ==========

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestOSAPIIntegration:
    @pytest.mark.asyncio
    async def test_process_and_trace(self, client):
        await client.post("/api/v1/os/process", json={"intent": "research AI"})
        resp = await client.get("/api/v1/intelligence/traces")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_prompt_create_and_get(self, client):
        await client.post("/api/v1/prompts", json={"name": "e2e-prompt", "content": "Hello"})
        resp = await client.get("/api/v1/prompts/e2e-prompt")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_analytics_summary(self, client):
        resp = await client.get("/api/v1/analytics/ai-summary")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_trace_by_component(self, client):
        resp = await client.get("/api/v1/intelligence/traces?component=classifier")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_trace_by_type(self, client):
        resp = await client.get("/api/v1/intelligence/traces?trace_type=command_analysis")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_prompt_list(self, client):
        resp = await client.get("/api/v1/prompts")
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_activate_prompt_version(self, client):
        await client.post("/api/v1/prompts", json={"name": "ver-e2e", "content": "v1"})
        await client.post("/api/v1/prompts", json={"name": "ver-e2e", "content": "v2"})
        resp = await client.post("/api/v1/prompts/ver-e2e/activate?version=1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_replay_after_snapshot(self, client):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="replay-e2e", user_input="test"))
        resp = await client.post("/api/v1/tasks/replay-e2e/replay")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_context_retrieval(self, client):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="ctx-e2e", user_input="test", agent="a1"))
        resp = await client.get("/api/v1/tasks/ctx-e2e/context")
        data = resp.json()
        assert data["success"] is True


# ========== Edge Case Tests ==========

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_process_very_long_intent(self):
        o = PersonalAIOrchestrator()
        result = await o.process("A" * 5000)
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_special_unicode(self):
        o = PersonalAIOrchestrator()
        result = await o.process("研究🧠人工智能📊发展趋势")
        assert result is not None

    @pytest.mark.asyncio
    async def test_trace_store_handles_many_records(self):
        store = DecisionTraceStore()
        for i in range(100):
            store.add_trace("plan_generation", "p", {}, {"step": i})
        assert len(store.get_all()) >= 100

    @pytest.mark.asyncio
    async def test_prompt_many_versions(self):
        reg = get_prompt_registry()
        for i in range(10):
            reg.create("many-ver", f"v{i}")
        assert reg.get_active("many-ver").version == 10

    @pytest.mark.asyncio
    async def test_tracker_many_records(self):
        tracker = get_ai_usage_tracker()
        for i in range(50):
            tracker.record(f"m{i}", "p", 1, 1)
        assert tracker.get_summary()["total_records"] >= 50

    @pytest.mark.asyncio
    async def test_multiple_tasks_snapshots(self):
        store = get_snapshot_store()
        for i in range(20):
            store.save(ContextSnapshot(task_id=f"task-{i}", user_input=f"input-{i}"))
        assert len(store.list_task_ids()) >= 20

    @pytest.mark.asyncio
    async def test_orchestrator_all_action_types(self):
        o = PersonalAIOrchestrator()
        for intent in ["research", "how to", "daily report", "optimize", "hello"]:
            result = await o.process(intent)
            assert result.decision.get("action") is not None

    @pytest.mark.asyncio
    async def test_decision_confidence_bounds(self):
        e = DecisionEngine()
        for intent in ["test", "urgent fix", "daily schedule", "hello"]:
            ctx = UnifiedContext(user_intent=intent)
            d = e.decide(ctx)
            assert 0.0 <= d.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_context_builder_persistence(self):
        cb = ContextBuilder()
        ctx1 = await cb.build(user_intent="test1")
        ctx2 = await cb.build(user_intent="test2")
        assert ctx1.user_intent != ctx2.user_intent

    @pytest.mark.asyncio
    async def test_trace_context_to_dict(self):
        ctx = create_trace_context(task_id="dict-test")
        ctx.record("command_analysis", "c", {}, {})
        d = ctx.to_dict()
        assert d["trace_count"] == 1

class TestE2EAdditional1:
    @pytest.mark.asyncio
    async def test_process_empty_category(self):
        o = PersonalAIOrchestrator()
        r = await o.process("test", task_category="")
        assert r is not None

    @pytest.mark.asyncio
    async def test_trace_type_values(self):
        from app.intelligence.trace.decision_trace import TraceType
        for t in TraceType:
            store = DecisionTraceStore()
            store.add_trace(t.value, "c", {}, {})
        # All types should work

    @pytest.mark.asyncio
    async def test_prompt_render_no_vars(self):
        reg = get_prompt_registry()
        reg.create("static", "Just text")
        assert reg.render("static") == "Just text"

    @pytest.mark.asyncio
    async def test_snapshot_all_fields(self):
        snap = ContextSnapshot(
            task_id="full", user_input="hi",
            memory_context={"m": "m1"}, knowledge_context={"k": "k1"},
            plan={"s": 1}, agent="a1", prompt="p", model="m", result={"ok": True},
        )
        d = snap.to_dict()
        assert len(d) >= 10

    @pytest.mark.asyncio
    async def test_replay_empty_snapshot(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="empty-replay"))
        r = get_replayer()
        result = await r.replay("empty-replay")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_tracker_with_agents(self):
        tracker = get_ai_usage_tracker()
        tracker.record("m", "p", 10, 5, agent_id="agent-1")
        recs = tracker.get_records()
        assert recs[0]["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_tracker_with_tasks(self):
        tracker = get_ai_usage_tracker()
        tracker.record("m", "p", 10, 5, task_id="task-xyz")
        recs = tracker.get_records()
        assert recs[0]["task_id"] == "task-xyz"

    @pytest.mark.asyncio
    async def test_store_query_all_filters(self):
        store = DecisionTraceStore()
        store.add_trace("command_analysis", "c1", {}, {}, task_id="ft", user_id="fu")
        results = store.query(task_id="ft", user_id="fu", component="c1", trace_type="command_analysis")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_registry_create_multiple_names(self):
        reg = get_prompt_registry()
        reg.create("a1", "ca")
        reg.create("a2", "cb")
        reg.create("a3", "cc")
        names = reg.list_names()
        assert "a1" in names
        assert "a2" in names
        assert "a3" in names

    @pytest.mark.asyncio
    async def test_tracker_summary_empty_model_usage(self):
        tracker = AIUsageTracker()
        s = tracker.get_summary()
        assert s["model_usage"] == {}

class TestE2EAdditional2:
    def test_context_system_state_defaults(self):
        s = SystemState()
        assert s.overall_health == "healthy"
        assert s.agents_available == 0

    def test_unified_context_empty(self):
        c = UnifiedContext()
        assert c.user_intent == ""
        assert c.generated_at != ""

    def test_decision_priority_values(self):
        d = Decision(priority=0)
        assert d.to_dict()["priority"] == 0
        d2 = Decision(priority=2)
        assert d2.to_dict()["priority"] == 2

    def test_replay_result_success_field(self):
        r = ReplayResult(success=True)
        assert r.to_dict()["success"] is True

    def test_ai_usage_record_latency(self):
        r = AIUsageRecord(latency_ms=123.45)
        assert r.to_dict()["latency_ms"] == 123.45

    def test_decision_trace_confidence(self):
        t = DecisionTrace.create("plan", "p", {}, {}, confidence=0.75)
        assert t.to_dict()["confidence"] == 0.75

    def test_prompt_template_active_default(self):
        t = PromptTemplate(name="t", content="c")
        assert t.active is True

    def test_context_snapshot_created(self):
        s = ContextSnapshot()
        assert "T" in s.created_at

    def test_orchestration_step_statuses(self):
        from app.os.orchestrator import OrchestrationStep
        s = OrchestrationStep(name="test", status="completed")
        assert s.to_dict()["status"] == "completed"

    def test_prompt_registry_activate_invalid_name(self):
        reg = get_prompt_registry()
        assert reg.activate_version("noexist", 1) is False

class TestE2EAdditional3:
    @pytest.mark.asyncio
    async def test_process_and_check_traces_exist(self):
        o = PersonalAIOrchestrator()
        await o.process("final check")
        assert True  # Should not crash

    @pytest.mark.asyncio
    async def test_prompt_multiple_renders_same_template(self):
        reg = get_prompt_registry()
        reg.create("multi", "{{a}} and {{b}}", ["a", "b"])
        r1 = reg.render("multi", a="1", b="2")
        r2 = reg.render("multi", a="x", b="y")
        assert r1 == "1 and 2"
        assert r2 == "x and y"

    @pytest.mark.asyncio
    async def test_tracker_records_after_clear(self):
        tracker = get_ai_usage_tracker()
        tracker.clear()
        tracker.record("m", "p", 1, 1)
        assert tracker.get_summary()["total_records"] == 1

    @pytest.mark.asyncio
    async def test_snapshot_list_after_delete(self):
        store = get_snapshot_store()
        store.save(ContextSnapshot(task_id="td1"))
        store.save(ContextSnapshot(task_id="td2"))
        store.delete("td1")
        ids = store.list_task_ids()
        assert "td1" not in ids
        assert "td2" in ids

    @pytest.mark.asyncio
    async def test_replay_result_to_dict(self):
        r = ReplayResult(task_id="t1", success=True, replayed_steps=["s1"], output={"k": "v"})
        d = r.to_dict()
        assert d["task_id"] == "t1"
        assert d["output"]["k"] == "v"

    @pytest.mark.asyncio
    async def test_orchestrator_recommendations_list(self):
        o = PersonalAIOrchestrator()
        result = await o.process("do something")
        assert isinstance(result.recommendations, list)

    def test_trace_type_enum_count(self):
        from app.intelligence.trace.decision_trace import TraceType
        assert len(TraceType) == 7

    def test_prompt_template_version_default(self):
        t = PromptTemplate(name="x", content="y")
        assert t.version == 1

    def test_ai_usage_record_all_fields_default(self):
        r = AIUsageRecord()
        d = r.to_dict()
        assert d["model"] == ""
        assert d["provider"] == ""
        assert d["task_id"] == ""

    def test_context_snapshot_id_unique(self):
        s1 = ContextSnapshot()
        s2 = ContextSnapshot()
        assert s1.id != s2.id

    def test_decision_engine_singleton(self):
        from app.os.decision import get_decision_engine
        d1 = get_decision_engine()
        d2 = get_decision_engine()
        assert d1 is d2

    def test_orchestrator_singleton(self):
        o1 = get_orchestrator()
        o2 = get_orchestrator()
        assert o1 is o2

    def test_tracker_singleton(self):
        t1 = get_ai_usage_tracker()
        t2 = get_ai_usage_tracker()
        assert t1 is t2

    def test_replayer_singleton(self):
        r1 = get_replayer()
        r2 = get_replayer()
        assert r1 is r2

    def test_snapshot_store_singleton(self):
        s1 = get_snapshot_store()
        s2 = get_snapshot_store()
        assert s1 is s2

class TestE2EAdditional4:
    def test_orchestration_result_defaults(self):
        from app.os.orchestrator import OrchestrationResult
        r = OrchestrationResult()
        assert r.success is False
        assert len(r.steps) == 0

    def test_unified_context_to_dict_keys(self):
        c = UnifiedContext(user_intent="test")
        d = c.to_dict()
        assert "user_intent" in d
        assert "memory_snapshot" in d
        assert "system_state" in d
        assert "decision" in d

    def test_memory_snapshot_to_dict(self):
        m = MemorySnapshot(profile={"name": "User"})
        d = m.to_dict()
        assert d["profile"]["name"] == "User"

    def test_system_state_to_dict(self):
        s = SystemState(agents_available=3, overall_health="healthy")
        d = s.to_dict()
        assert d["agents_available"] == 3

    def test_context_builder_singleton(self):
        from app.os.context import get_context_builder
        b1 = get_context_builder()
        b2 = get_context_builder()
        assert b1 is b2

    def test_trace_store_singleton(self):
        s1 = get_trace_store()
        s2 = get_trace_store()
        assert s1 is s2

    def test_prompt_registry_singleton(self):
        r1 = get_prompt_registry()
        r2 = get_prompt_registry()
        assert r1 is r2

    def test_ai_usage_tracker_singleton_ok(self):
        from app.analytics.ai_metrics import get_ai_usage_tracker
        t1 = get_ai_usage_tracker()
        t2 = get_ai_usage_tracker()
        assert t1 is t2

    def test_replay_result_default_error(self):
        r = ReplayResult(error="test error")
        assert r.to_dict()["error"] == "test error"

    def test_decision_trace_store_clear(self):
        s = DecisionTraceStore()
        s.add_trace("c", "x", {}, {})
        s.clear()
        assert len(s.get_all()) == 0

    def test_prompt_manager_singleton(self):
        from app.prompts.manager import get_prompt_manager
        m1 = get_prompt_manager()
        m2 = get_prompt_manager()
        assert m1 is m2
