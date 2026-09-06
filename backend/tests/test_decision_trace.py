"""Phase 5.11 tests - Decision Trace System"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.intelligence.trace.decision_trace import DecisionTrace, TraceType
from app.intelligence.trace.decision_store import DecisionTraceStore, get_trace_store
from app.intelligence.trace.trace_context import TraceContext, create_trace_context
from app.main import app


# ========== TraceType ==========

class TestTraceType:
    def test_values(self):
        assert TraceType.COMMAND_ANALYSIS == "command_analysis"
        assert TraceType.PLAN_GENERATION == "plan_generation"
        assert TraceType.MEMORY_RETRIEVAL == "memory_retrieval"
        assert TraceType.AGENT_SELECTION == "agent_selection"

    def test_count(self):
        assert len(TraceType) == 7


# ========== DecisionTrace ==========

class TestDecisionTrace:
    def test_default(self):
        t = DecisionTrace()
        assert t.id != ""
        assert t.trace_type == ""

    def test_create(self):
        t = DecisionTrace.create(
            trace_type="command_analysis",
            component="classifier",
            input_data={"intent": "research"},
            decision={"action": "create_task"},
            reason="Keyword match",
            confidence=0.85,
        )
        assert t.trace_type == "command_analysis"
        assert t.confidence == 0.85

    def test_to_dict(self):
        t = DecisionTrace.create(
            trace_type="plan_generation",
            component="planner",
            input_data={"task": "research AI"},
            decision={"steps": 3},
            reason="DAG generated",
            confidence=0.9,
            task_id="task-1",
            user_id="user-1",
        )
        d = t.to_dict()
        assert d["trace_type"] == "plan_generation"
        assert d["task_id"] == "task-1"
        assert d["user_id"] == "user-1"

    def test_create_with_metadata(self):
        t = DecisionTrace.create(
            trace_type="agent_selection",
            component="selector",
            input_data={},
            decision={"agent": "a1"},
            metadata={"score": 0.95},
        )
        assert t.metadata["score"] == 0.95

    def test_generated_at_is_iso(self):
        t = DecisionTrace.create(
            trace_type="memory_retrieval",
            component="memory",
            input_data={},
            decision={"found": 3},
        )
        assert "T" in t.created_at

# ========== DecisionTraceStore ==========

class TestDecisionTraceStore:
    def test_add_trace(self):
        s = DecisionTraceStore()
        s.add_trace(
            trace_type="command_analysis",
            component="classifier",
            input_data={"intent": "test"},
            decision={"action": "chat"},
        )
        assert len(s.get_all()) == 1

    def test_add_multiple(self):
        s = DecisionTraceStore()
        for i in range(5):
            s.add_trace(
                trace_type="plan_generation",
                component="planner",
                input_data={},
                decision={"step": i},
            )
        assert len(s.get_all()) == 5

    def test_query_by_task_id(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="command_analysis", component="c", input_data={}, decision={}, task_id="t1")
        s.add_trace(trace_type="agent_selection", component="s", input_data={}, decision={}, task_id="t2")
        s.add_trace(trace_type="plan_generation", component="p", input_data={}, decision={}, task_id="t1")
        results = s.query(task_id="t1")
        assert len(results) == 2

    def test_query_by_user_id(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="command_analysis", component="c", input_data={}, decision={}, user_id="u1")
        s.add_trace(trace_type="plan_generation", component="p", input_data={}, decision={}, user_id="u2")
        results = s.query(user_id="u1")
        assert len(results) == 1

    def test_query_by_component(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="command_analysis", component="classifier", input_data={}, decision={})
        s.add_trace(trace_type="plan_generation", component="planner", input_data={}, decision={})
        s.add_trace(trace_type="agent_selection", component="classifier", input_data={}, decision={})
        results = s.query(component="classifier")
        assert len(results) == 2

    def test_query_by_trace_type(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="command_analysis", component="c", input_data={}, decision={})
        s.add_trace(trace_type="plan_generation", component="p", input_data={}, decision={})
        s.add_trace(trace_type="command_analysis", component="d", input_data={}, decision={})
        results = s.query(trace_type="command_analysis")
        assert len(results) == 2

    def test_query_combined_filters(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="command_analysis", component="classifier", input_data={}, decision={}, task_id="t1")
        s.add_trace(trace_type="command_analysis", component="classifier", input_data={}, decision={}, task_id="t2")
        s.add_trace(trace_type="plan_generation", component="classifier", input_data={}, decision={}, task_id="t1")
        results = s.query(task_id="t1", trace_type="command_analysis")
        assert len(results) == 1

    def test_query_limit(self):
        s = DecisionTraceStore()
        for i in range(20):
            s.add_trace(trace_type="plan_generation", component="p", input_data={}, decision={})
        results = s.query(limit=5)
        assert len(results) == 5

    def test_query_offset(self):
        s = DecisionTraceStore()
        for i in range(10):
            s.add_trace(trace_type="plan_generation", component="p", input_data={}, decision={"i": i})
        results = s.query(limit=3, offset=7)
        assert len(results) == 3

    def test_get_by_task(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="command_analysis", component="c", input_data={}, decision={}, task_id="task-x")
        traces = s.get_by_task("task-x")
        assert len(traces) == 1

    def test_get_by_task_nonexistent(self):
        s = DecisionTraceStore()
        traces = s.get_by_task("nonexistent")
        assert len(traces) == 0

    def test_clear(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="command_analysis", component="c", input_data={}, decision={})
        s.clear()
        assert len(s.get_all()) == 0

    def test_singleton(self):
        s1 = get_trace_store()
        s2 = get_trace_store()
        assert s1 is s2

# ========== TraceContext ==========

class TestTraceContext:
    def test_create_context(self):
        ctx = create_trace_context(task_id="t1", user_id="u1")
        assert ctx.task_id == "t1"
        assert ctx.user_id == "u1"

    def test_record_trace(self):
        ctx = create_trace_context(task_id="t1")
        ctx.record(
            trace_type="command_analysis",
            component="classifier",
            input_data={"intent": "test"},
            decision={"action": "chat"},
        )
        assert len(ctx.get_traces()) == 1

    def test_record_multiple(self):
        ctx = create_trace_context(task_id="t2")
        ctx.record(trace_type="command_analysis", component="c", input_data={}, decision={})
        ctx.record(trace_type="plan_generation", component="p", input_data={}, decision={})
        ctx.record(trace_type="agent_selection", component="s", input_data={}, decision={})
        assert len(ctx.get_traces()) == 3

    def test_to_dict(self):
        ctx = create_trace_context(task_id="t1", user_id="u1")
        ctx.record(trace_type="command_analysis", component="c", input_data={}, decision={})
        d = ctx.to_dict()
        assert d["task_id"] == "t1"
        assert d["trace_count"] == 1

    def test_trace_in_store(self):
        ctx = create_trace_context(task_id="t3")
        ctx.record(trace_type="final_result", component="orchestrator", input_data={}, decision={})
        store = get_trace_store()
        traces = store.get_by_task("t3")
        assert len(traces) >= 1


# ========== API Tests ==========

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestTraceAPI:
    @pytest.mark.asyncio
    async def test_get_traces_200(self, client):
        resp = await client.get("/api/v1/intelligence/traces")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_traces_structure(self, client):
        resp = await client.get("/api/v1/intelligence/traces")
        data = resp.json()
        assert data["success"] is True
        assert "traces" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_traces_with_filter(self, client):
        resp = await client.get("/api/v1/intelligence/traces?task_id=t1")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_traces_with_component(self, client):
        resp = await client.get("/api/v1/intelligence/traces?component=planner")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_traces_with_type(self, client):
        resp = await client.get("/api/v1/intelligence/traces?trace_type=plan_generation")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_task_decision_trace(self, client):
        resp = await client.get("/api/v1/intelligence/tasks/t1/decision-trace")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_task_decision_trace_structure(self, client):
        resp = await client.get("/api/v1/intelligence/tasks/t1/decision-trace")
        data = resp.json()
        assert "task_id" in data
        assert "traces" in data
        assert "total" in data

class TestTraceExtra:
    def test_trace_types_all_defined(self):
        types = [t.value for t in TraceType]
        assert "command_analysis" in types
        assert "final_result" in types
        assert "tool_selection" in types

    def test_empty_store_query(self):
        s = DecisionTraceStore()
        r = s.query()
        assert r == []

    def test_trace_confidence_bounds(self):
        t = DecisionTrace.create(trace_type="plan_generation", component="p", input_data={}, decision={}, confidence=1.0)
        assert 0 <= t.confidence <= 1

    def test_trace_id_unique(self):
        t1 = DecisionTrace()
        t2 = DecisionTrace()
        assert t1.id != t2.id

    def test_store_add_via_obj(self):
        s = DecisionTraceStore()
        t = DecisionTrace.create(trace_type="memory_retrieval", component="m", input_data={}, decision={})
        s.add(t)
        assert len(s.get_all()) == 1

    def test_context_default_values(self):
        ctx = TraceContext()
        assert ctx.task_id == ""
        assert ctx.user_id == ""

    def test_store_all_traces_returned(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="command_analysis", component="c1", input_data={}, decision={})
        s.add_trace(trace_type="plan_generation", component="c2", input_data={}, decision={})
        assert len(s.get_all()) == 2

    def test_trace_record_reason(self):
        s = DecisionTraceStore()
        s.add_trace(trace_type="agent_selection", component="s", input_data={}, decision={}, reason="Best match")
        results = s.get_all()
        assert results[0]["reason"] == "Best match"
