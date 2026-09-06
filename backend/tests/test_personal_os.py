"""Phase 5.10 tests - Personal AI OS"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.os.context import (
    MemorySnapshot, SystemState, UnifiedContext,
    ContextBuilder, get_context_builder,
)
from app.os.decision import Decision, DecisionEngine, get_decision_engine
from app.os.orchestrator import (
    OrchestrationStep, OrchestrationResult,
    PersonalAIOrchestrator, get_orchestrator,
)
from app.main import app


# ========== MemorySnapshot ==========

class TestMemorySnapshot:
    def test_default(self):
        m = MemorySnapshot()
        assert m.profile == {}
        assert m.preferences == []
        assert m.recent_experiences == []

    def test_to_dict(self):
        m = MemorySnapshot(
            profile={"name": "User1"},
            preferences=[{"key": "dark_mode"}],
            recent_experiences=[{"task": "research"}],
            relevant_knowledge=["AI trends"],
        )
        d = m.to_dict()
        assert d["profile"]["name"] == "User1"
        assert len(d["preferences"]) == 1
        assert len(d["recent_experiences"]) == 1
        assert d["relevant_knowledge"][0] == "AI trends"


# ========== SystemState ==========

class TestSystemState:
    def test_default(self):
        s = SystemState()
        assert s.agents_available == 0
        assert s.overall_health == "healthy"

    def test_to_dict(self):
        s = SystemState(agents_available=5, agents_active=3, tasks_running=2)
        d = s.to_dict()
        assert d["agents_available"] == 5
        assert d["agents_active"] == 3
        assert d["tasks_running"] == 2


# ========== UnifiedContext ==========

class TestUnifiedContext:
    def test_default(self):
        c = UnifiedContext()
        assert c.user_intent == ""
        assert c.generated_at != ""

    def test_to_dict_structure(self):
        c = UnifiedContext(user_intent="Test intent", task_category="chat")
        d = c.to_dict()
        assert d["user_intent"] == "Test intent"
        assert d["task_category"] == "chat"
        assert "memory_snapshot" in d
        assert "system_state" in d
        assert "decision" in d

    def test_to_dict_with_all_fields(self):
        c = UnifiedContext(
            user_intent="Research AI",
            task_category="research",
            memory_snapshot=MemorySnapshot(recent_experiences=[{"task": "prev"}]),
            system_state=SystemState(agents_available=3),
            recommended_agents=["agent-1"],
            improvement_suggestions=[{"type": "bottleneck"}],
        )
        d = c.to_dict()
        assert len(d["memory_snapshot"]["recent_experiences"]) == 1
        assert d["system_state"]["agents_available"] == 3
        assert len(d["recommended_agents"]) == 1

# ========== ContextBuilder ==========

class TestContextBuilder:
    @pytest.mark.asyncio
    async def test_build_empty(self):
        b = ContextBuilder()
        ctx = await b.build()
        assert isinstance(ctx, UnifiedContext)
        assert ctx.user_intent == ""

    @pytest.mark.asyncio
    async def test_build_with_intent(self):
        b = ContextBuilder()
        ctx = await b.build(user_intent="Research AI", task_category="research")
        assert ctx.user_intent == "Research AI"
        assert ctx.task_category == "research"

    @pytest.mark.asyncio
    async def test_build_with_agent_runtime(self):
        class FakeRT:
            def list_agents(self):
                return [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]
            def list_running_agents(self):
                return [{"id": "a1"}]
        b = ContextBuilder()
        b.set_agent_runtime(FakeRT())
        ctx = await b.build()
        assert ctx.system_state.agents_available == 3
        assert ctx.system_state.agents_active == 1

    @pytest.mark.asyncio
    async def test_build_with_task_store(self):
        class FakeStore:
            async def list_tasks(self):
                return [
                    {"task_id": "t1", "status": "running"},
                    {"task_id": "t2", "status": "pending"},
                    {"task_id": "t3", "status": "completed"},
                ]
        b = ContextBuilder()
        b.set_task_store(FakeStore())
        ctx = await b.build()
        assert ctx.system_state.tasks_running == 1
        assert ctx.system_state.tasks_queued == 1

    @pytest.mark.asyncio
    async def test_build_with_memory_service(self):
        class FakeMem:
            async def search_memory(self, query):
                return [{"id": "m1", "text": "Previous research"}, {"id": "m2", "text": "Another"}]
        b = ContextBuilder()
        b.set_memory_service(FakeMem())
        ctx = await b.build(user_intent="research")
        assert len(ctx.memory_snapshot.recent_experiences) >= 1

    @pytest.mark.asyncio
    async def test_build_handles_exceptions(self):
        class BadRT:
            def list_agents(self):
                raise RuntimeError("boom")
        b = ContextBuilder()
        b.set_agent_runtime(BadRT())
        ctx = await b.build()
        assert ctx.system_state.agents_available == 0  # graceful

    @pytest.mark.asyncio
    async def test_singleton_builder(self):
        b1 = get_context_builder()
        b2 = get_context_builder()
        assert b1 is b2

# ========== Decision ==========

class TestDecision:
    def test_default(self):
        d = Decision()
        assert d.action == ""
        assert d.confidence == 0.0

    def test_to_dict(self):
        d = Decision(action="create_task", confidence=0.8, reasoning="Test",
                     task_description="Do research", recommended_agents=["a1"],
                     should_automate=False, should_learn=True, priority=1)
        dd = d.to_dict()
        assert dd["action"] == "create_task"
        assert dd["confidence"] == round(0.8, 3)
        assert dd["recommended_agents"] == ["a1"]
        assert dd["should_learn"] is True
        assert dd["priority"] == 1

    def test_confidence_rounding(self):
        d = Decision(confidence=0.33333)
        assert d.to_dict()["confidence"] == 0.333


# ========== DecisionEngine ==========

class TestDecisionEngine:
    def test_decide_empty(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="")
        d = e.decide(ctx)
        assert isinstance(d, Decision)
        assert d.action in ("suggest", "chat", "query", "create_task", "automate", "improve")

    def test_decide_research_intent(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="Research AI trends")
        d = e.decide(ctx)
        assert d.action == "create_task"

    def test_decide_analyze_intent(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="analyze the report")
        d = e.decide(ctx)
        assert d.action == "create_task"

    def test_decide_query_intent(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="how does AI work")
        d = e.decide(ctx)
        assert d.action == "query"

    def test_decide_automate_intent(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="daily report generation")
        d = e.decide(ctx)
        assert d.action == "automate"

    def test_decide_improve_intent(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="optimize my workflow")
        d = e.decide(ctx)
        assert d.action == "improve"

    def test_decide_with_agents_available(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="write a blog post",
                             system_state=SystemState(agents_available=4))
        d = e.decide(ctx)
        assert d.confidence > 0.3

    def test_decide_with_memories(self):
        e = DecisionEngine()
        ctx = UnifiedContext(
            user_intent="research ML",
            memory_snapshot=MemorySnapshot(recent_experiences=[{"task": "prev"}]),
        )
        d = e.decide(ctx)
        assert d.confidence > 0.3

    def test_decide_priority_urgent(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="urgent fix the bug")
        d = e.decide(ctx)
        assert d.priority == 2

    def test_decide_should_learn(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="research",
                             system_state=SystemState(agents_available=3))
        d = e.decide(ctx)
        assert d.should_learn is True

    def test_decide_should_automate_daily(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="daily standup report")
        d = e.decide(ctx)
        assert d.should_automate is True

    def test_decide_reasoning_non_empty(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="analyze data")
        d = e.decide(ctx)
        assert len(d.reasoning) > 0

    def test_singleton_engine(self):
        d1 = get_decision_engine()
        d2 = get_decision_engine()
        assert d1 is d2

# ========== OrchestrationStep ==========

class TestOrchestrationStep:
    def test_default(self):
        s = OrchestrationStep(name="test")
        assert s.name == "test"
        assert s.status == "pending"

    def test_to_dict(self):
        s = OrchestrationStep(name="memory_retrieval", status="completed",
                              result={"found": 3}, duration_ms=12.5)
        d = s.to_dict()
        assert d["name"] == "memory_retrieval"
        assert d["status"] == "completed"
        assert d["result"]["found"] == 3
        assert d["duration_ms"] == 12.5

    def test_failed_step(self):
        s = OrchestrationStep(name="planning", status="failed", error="Boom")
        d = s.to_dict()
        assert d["status"] == "failed"
        assert d["error"] == "Boom"


# ========== OrchestrationResult ==========

class TestOrchestrationResult:
    def test_default(self):
        r = OrchestrationResult()
        assert r.success is False
        assert r.user_intent == ""

    def test_to_dict(self):
        r = OrchestrationResult(
            id="abc", user_intent="test", success=True,
            decision={"action": "chat"}, task_id="task-1",
            recommendations=["R1"],
        )
        d = r.to_dict()
        assert d["id"] == "abc"
        assert d["success"] is True
        assert d["decision"]["action"] == "chat"
        assert d["task_id"] == "task-1"
        assert len(d["recommendations"]) == 1

    def test_to_dict_with_steps(self):
        r = OrchestrationResult(
            steps=[OrchestrationStep(name="s1", status="completed").to_dict()],
            context={"user_intent": "test"},
        )
        d = r.to_dict()
        assert len(d["steps"]) == 1
        assert d["context"]["user_intent"] == "test"

# ========== PersonalAIOrchestrator ==========

class TestPersonalAIOrchestrator:
    @pytest.mark.asyncio
    async def test_process_basic(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Hello")
        assert isinstance(result, OrchestrationResult)
        assert result.user_intent == "Hello"
        assert len(result.steps) == 5

    @pytest.mark.asyncio
    async def test_process_empty_intent(self):
        o = PersonalAIOrchestrator()
        result = await o.process("")
        assert isinstance(result, OrchestrationResult)

    @pytest.mark.asyncio
    async def test_process_produces_steps(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Research AI")
        step_names = [s["name"] for s in result.steps]
        assert "memory_retrieval" in step_names
        assert "decision" in step_names
        assert "planning" in step_names
        assert "agent_selection" in step_names
        assert "learning" in step_names

    @pytest.mark.asyncio
    async def test_process_all_steps_completed_or_skipped(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        for step in result.steps:
            assert step["status"] in ("completed", "skipped", "failed")

    @pytest.mark.asyncio
    async def test_process_result_to_dict(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Write a report")
        d = result.to_dict()
        assert "id" in d
        assert "steps" in d
        assert "decision" in d
        assert "context" in d

    @pytest.mark.asyncio
    async def test_process_with_category(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Code a function", task_category="coding")
        assert result.user_intent == "Code a function"

    @pytest.mark.asyncio
    async def test_process_generates_recommendations(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Do something new")
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_process_has_decision(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Analyze data")
        assert result.decision.get("action") in (
            "create_task", "query", "chat", "suggest", "automate", "improve"
        )

    @pytest.mark.asyncio
    async def test_singleton(self):
        o1 = get_orchestrator()
        o2 = get_orchestrator()
        assert o1 is o2

    @pytest.mark.asyncio
    async def test_process_generates_unique_ids(self):
        o = PersonalAIOrchestrator()
        r1 = await o.process("Task 1")
        r2 = await o.process("Task 2")
        assert r1.id != r2.id


# ========== API Tests ==========

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestOSAPI:
    @pytest.mark.asyncio
    async def test_process_200(self, client):
        resp = await client.post("/api/v1/os/process", json={"intent": "Research AI"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_process_has_result(self, client):
        resp = await client.post("/api/v1/os/process", json={"intent": "Write code"})
        data = resp.json()
        assert data["success"] is True
        assert "result" in data

    @pytest.mark.asyncio
    async def test_process_empty_intent(self, client):
        resp = await client.post("/api/v1/os/process", json={"intent": ""})
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_process_with_category(self, client):
        resp = await client.post("/api/v1/os/process", json={"intent": "Code", "task_category": "coding"})
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_process_result_has_steps(self, client):
        resp = await client.post("/api/v1/os/process", json={"intent": "Analyze data"})
        data = resp.json()
        assert "steps" in data["result"]

    @pytest.mark.asyncio
    async def test_get_status_200(self, client):
        resp = await client.get("/api/v1/os/status")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_status_structure(self, client):
        resp = await client.get("/api/v1/os/status")
        data = resp.json()
        assert data["success"] is True
        assert "os_version" in data
        assert "components" in data
        assert "system_state" in data

    @pytest.mark.asyncio
    async def test_get_insights_200(self, client):
        resp = await client.get("/api/v1/os/insights")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_insights_structure(self, client):
        resp = await client.get("/api/v1/os/insights")
        data = resp.json()
        assert data["success"] is True
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

# ========== Extended Context Tests ==========

class TestContextBuilderExtended:
    @pytest.mark.asyncio
    async def test_build_improvement_suggestions(self):
        class FakeImprovement:
            async def analyze(self):
                class Report:
                    bottlenecks = [{"type": "slow", "suggestion": "Fix"}]
                return Report()
        b = ContextBuilder()
        b.set_improvement_engine(FakeImprovement())
        ctx = await b.build()
        assert len(ctx.improvement_suggestions) >= 1

    @pytest.mark.asyncio
    async def test_build_empty_agents(self):
        class FakeRT:
            def list_agents(self):
                return []
            def list_running_agents(self):
                return []
        b = ContextBuilder()
        b.set_agent_runtime(FakeRT())
        ctx = await b.build()
        assert ctx.system_state.agents_available == 0
        assert ctx.system_state.agents_active == 0

    @pytest.mark.asyncio
    async def test_build_empty_task_store(self):
        class FakeStore:
            async def list_tasks(self):
                return []
        b = ContextBuilder()
        b.set_task_store(FakeStore())
        ctx = await b.build()
        assert ctx.system_state.tasks_running == 0

    @pytest.mark.asyncio
    async def test_build_with_planner(self):
        class FakePlanner:
            pass
        b = ContextBuilder()
        b.set_planner(FakePlanner())
        ctx = await b.build()
        assert isinstance(ctx, UnifiedContext)

    @pytest.mark.asyncio
    async def test_build_full_stack(self):
        class FakeRT:
            def list_agents(self):
                return [{"id": "a1"}, {"id": "a2"}]
            def list_running_agents(self):
                return [{"id": "a1"}]
        class FakeStore:
            async def list_tasks(self):
                return [{"task_id": "t1", "status": "running"}]
        class FakeMem:
            async def search_memory(self, q):
                return [{"text": "past"}]
        b = ContextBuilder()
        b.set_agent_runtime(FakeRT())
        b.set_task_store(FakeStore())
        b.set_memory_service(FakeMem())
        ctx = await b.build(user_intent="research")
        assert ctx.system_state.agents_available == 2
        assert ctx.system_state.agents_active == 1
        assert ctx.system_state.tasks_running == 1
        assert len(ctx.memory_snapshot.recent_experiences) == 1


# ========== Extended Decision Tests ==========

class TestDecisionEngineExtended:
    def test_decide_build_task(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="build a website")
        d = e.decide(ctx)
        assert d.action == "create_task"

    def test_decide_generate_content(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="generate weekly report")
        d = e.decide(ctx)
        assert d.action == "create_task"

    def test_decide_explain_topic(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="explain quantum computing")
        d = e.decide(ctx)
        assert d.action == "query"

    def test_decide_every_keyword(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="every morning at 8")
        d = e.decide(ctx)
        assert d.action == "automate"
        assert d.should_automate is True

    def test_decide_confidence_with_agents_and_memories(self):
        e = DecisionEngine()
        ctx = UnifiedContext(
            user_intent="research",
            system_state=SystemState(agents_available=5),
            memory_snapshot=MemorySnapshot(recent_experiences=[{"task": "x"}]),
            recommended_agents=["a1"],
            improvement_suggestions=[{"type": "test"}],
        )
        d = e.decide(ctx)
        assert d.confidence >= 0.7

    def test_decide_priority_medium_with_suggestions(self):
        e = DecisionEngine()
        ctx = UnifiedContext(
            user_intent="do something",
            improvement_suggestions=[{"type": "bottleneck"}],
        )
        d = e.decide(ctx)
        assert d.priority >= 1

    def test_decide_critical_priority(self):
        e = DecisionEngine()
        ctx = UnifiedContext(user_intent="critical security fix")
        d = e.decide(ctx)
        assert d.priority == 2

# ========== Extended Orchestrator Tests ==========

class TestOrchestratorExtended:
    @pytest.mark.asyncio
    async def test_process_automate_intent(self):
        o = PersonalAIOrchestrator()
        result = await o.process("daily backup every day")
        assert result.decision.get("action") == "automate"

    @pytest.mark.asyncio
    async def test_process_improve_intent(self):
        o = PersonalAIOrchestrator()
        result = await o.process("optimize performance")
        assert result.decision.get("action") == "improve"

    @pytest.mark.asyncio
    async def test_process_query_intent(self):
        o = PersonalAIOrchestrator()
        result = await o.process("what is machine learning")
        assert result.decision.get("action") == "query"

    @pytest.mark.asyncio
    async def test_process_result_id_not_empty(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        assert len(result.id) > 0

    @pytest.mark.asyncio
    async def test_process_generated_at_is_iso(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        assert "T" in result.generated_at

    @pytest.mark.asyncio
    async def test_process_decision_has_confidence(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Research AI trends")
        assert "confidence" in result.decision

    @pytest.mark.asyncio
    async def test_process_context_has_system_state(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        assert "system_state" in result.context

    @pytest.mark.asyncio
    async def test_process_step_durations(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        for step in result.steps:
            assert "duration_ms" in step
            assert step["duration_ms"] >= 0


# ========== Extended API Tests ==========

class TestOSAPIExtended:
    @pytest.mark.asyncio
    async def test_process_large_intent(self, client):
        resp = await client.post("/api/v1/os/process", json={"intent": "A" * 200})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_process_chinese_intent(self, client):
        resp = await client.post("/api/v1/os/process", json={"intent": "研究人工智能趋势"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_status_has_agents(self, client):
        resp = await client.get("/api/v1/os/status")
        data = resp.json()
        assert "agents_available" in data
        assert "agents_active" in data

    @pytest.mark.asyncio
    async def test_status_has_tasks(self, client):
        resp = await client.get("/api/v1/os/status")
        data = resp.json()
        assert "tasks_running" in data
        assert "tasks_queued" in data

    @pytest.mark.asyncio
    async def test_status_overall_health(self, client):
        resp = await client.get("/api/v1/os/status")
        data = resp.json()
        assert data["overall_health"] in ("healthy", "degraded")

    @pytest.mark.asyncio
    async def test_insights_has_decision(self, client):
        resp = await client.get("/api/v1/os/insights")
        data = resp.json()
        assert "decision" in data

    @pytest.mark.asyncio
    async def test_insights_has_context(self, client):
        resp = await client.get("/api/v1/os/insights")
        data = resp.json()
        assert "context" in data

    @pytest.mark.asyncio
    async def test_insights_suggestions_list(self, client):
        resp = await client.get("/api/v1/os/insights")
        data = resp.json()
        assert len(data["suggestions"]) >= 1

# ========== Integration Tests ==========

class TestOSIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_context_builder(self):
        o = get_orchestrator()
        cb = get_context_builder()
        # Wire them up
        o.set_context_builder(cb)
        o.set_decision_engine(get_decision_engine())
        result = await o.process("Research machine learning applications")
        assert isinstance(result, OrchestrationResult)
        assert len(result.steps) == 5

    @pytest.mark.asyncio
    async def test_multiple_intents_different_decisions(self):
        o = PersonalAIOrchestrator()
        r1 = await o.process("research AI")
        r2 = await o.process("how does it work")
        r3 = await o.process("daily report")
        assert r1.decision.get("action") != r2.decision.get("action") or r1.decision.get("action") != r3.decision.get("action")

    @pytest.mark.asyncio
    async def test_orchestrator_graceful_on_all_subsystems_unavailable(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        assert isinstance(result, OrchestrationResult)

    @pytest.mark.asyncio
    async def test_process_with_long_intent(self):
        o = PersonalAIOrchestrator()
        long_intent = "Please analyze the quarterly financial report and provide a detailed summary with recommendations " * 3
        result = await o.process(long_intent)
        assert result.user_intent == long_intent

    @pytest.mark.asyncio
    async def test_process_special_characters(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test with special chars: @#$%^&*()")
        assert isinstance(result, OrchestrationResult)

    @pytest.mark.asyncio
    async def test_process_unicode(self):
        o = PersonalAIOrchestrator()
        result = await o.process("研究AI并撰写报告")
        assert result.user_intent == "研究AI并撰写报告"

    @pytest.mark.asyncio
    async def test_api_process_missing_body(self, client):
        resp = await client.post("/api/v1/os/process", json={})
        assert resp.status_code == 422  # validation error

    @pytest.mark.asyncio
    async def test_api_status_fast(self, client):
        import time
        t0 = time.time()
        await client.get("/api/v1/os/status")
        assert (time.time() - t0) < 5.0

    @pytest.mark.asyncio
    async def test_api_insights_fast(self, client):
        import time
        t0 = time.time()
        await client.get("/api/v1/os/insights")
        assert (time.time() - t0) < 5.0

    @pytest.mark.asyncio
    async def test_result_context_memory_snapshot(self):
        o = PersonalAIOrchestrator()
        result = await o.process("research")
        ctx = result.context
        assert "memory_snapshot" in ctx

    @pytest.mark.asyncio
    async def test_result_steps_each_has_status(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        for s in result.steps:
            assert s["status"] in ("pending", "running", "completed", "skipped", "failed")

    @pytest.mark.asyncio
    async def test_result_decision_action_is_string(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        assert isinstance(result.decision.get("action"), str)

    @pytest.mark.asyncio
    async def test_result_decision_confidence_is_float(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        assert isinstance(result.decision.get("confidence"), (int, float))

    @pytest.mark.asyncio
    async def test_result_recommendations_list(self):
        o = PersonalAIOrchestrator()
        result = await o.process("Test")
        assert isinstance(result.recommendations, list)

    @pytest.mark.asyncio
    async def test_result_task_id_empty_for_chat(self):
        o = PersonalAIOrchestrator()
        result = await o.process("hello how are you")
        # For chat actions, task_id might remain empty since no task is created
        assert isinstance(result.task_id, str)

    @pytest.mark.asyncio
    async def test_api_process_with_task_category(self, client):
        resp = await client.post("/api/v1/os/process", json={
            "intent": "Write code", "task_category": "coding",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_api_process_result_id_unique(self, client):
        r1 = await client.post("/api/v1/os/process", json={"intent": "A"})
        r2 = await client.post("/api/v1/os/process", json={"intent": "B"})
        id1 = r1.json()["result"]["id"]
        id2 = r2.json()["result"]["id"]
        assert id1 != id2
