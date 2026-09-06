"""Phase 5.7 tests - Personal Dashboard"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.analytics.metrics import PersonalMetrics, PersonalMetricsCollector
from app.analytics.insight import Insight, AIInsightGenerator, get_insight_generator
from app.main import app


class TestPersonalMetrics:
    def test_default_values(self):
        m = PersonalMetrics()
        assert m.tasks_today == 0
        assert m.tasks_completed_today == 0
        assert m.generated_at != ""

    def test_to_dict_structure(self):
        m = PersonalMetrics(tasks_today=5, tasks_completed_today=3)
        d = m.to_dict()
        assert d["tasks_today"] == 5
        assert "efficiency" in d
        assert "knowledge_growth" in d
        assert "agent_activity" in d

    def test_efficiency_sub_dict(self):
        m = PersonalMetrics(success_rate=0.85, average_duration_ms=1200.0, total_iterations=10)
        d = m.to_dict()
        assert d["efficiency"]["success_rate"] == round(0.85, 3)
        assert d["efficiency"]["average_duration_ms"] == 1200.0

    def test_knowledge_growth_sub_dict(self):
        m = PersonalMetrics(knowledge_items_added=3, experience_records_created=2, artifacts_generated=5)
        d = m.to_dict()
        assert d["knowledge_growth"]["knowledge_items_added"] == 3

    def test_agent_activity_sub_dict(self):
        m = PersonalMetrics(agents_active=2, agents_total=4, agent_executions_today=8)
        d = m.to_dict()
        assert d["agent_activity"]["agents_active"] == 2

    def test_to_dict_all_zero(self):
        m = PersonalMetrics()
        d = m.to_dict()
        assert d["tasks_today"] == 0

class TestPersonalMetricsCollector:
    @pytest.mark.asyncio
    async def test_collect_empty(self):
        c = PersonalMetricsCollector()
        m = await c.collect()
        assert isinstance(m, PersonalMetrics)
        assert m.tasks_today == 0

    @pytest.mark.asyncio
    async def test_collect_with_task_store_empty(self):
        class FakeStore:
            async def list_tasks(self):
                return []
        c = PersonalMetricsCollector()
        c.set_task_store(FakeStore())
        m = await c.collect()
        assert m.tasks_today == 0

    @pytest.mark.asyncio
    async def test_collect_with_task_store_data(self):
        today = datetime.now(timezone.utc).isoformat()
        class FakeStore:
            async def list_tasks(self):
                return [
                    {"task_id": "t1", "created_at": today, "status": "completed"},
                    {"task_id": "t2", "created_at": today, "status": "completed"},
                    {"task_id": "t3", "created_at": today, "status": "failed"},
                    {"task_id": "t4", "created_at": today, "status": "running"},
                ]
        c = PersonalMetricsCollector()
        c.set_task_store(FakeStore())
        m = await c.collect()
        assert m.tasks_today == 4
        assert m.tasks_completed_today == 2
        assert m.tasks_failed_today == 1
        assert m.tasks_running == 1

    @pytest.mark.asyncio
    async def test_collect_with_agent_runtime(self):
        class FakeRuntime:
            def list_running_agents(self):
                return [{"id": "a1"}, {"id": "a2"}]
            def list_agents(self):
                return [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}, {"id": "a4"}]
        c = PersonalMetricsCollector()
        c.set_agent_runtime(FakeRuntime())
        m = await c.collect()
        assert m.agents_active == 2
        assert m.agents_total == 4

    @pytest.mark.asyncio
    async def test_collect_with_experience_service(self):
        class FakeExp:
            _records = [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}]
        c = PersonalMetricsCollector()
        c.set_experience_service(FakeExp())
        m = await c.collect()
        assert m.experience_records_created == 3

    @pytest.mark.asyncio
    async def test_collect_with_workspace(self):
        class FakeItem:
            def __init__(self):
                self.items = [{"id": "i1"}, {"id": "i2"}]
        class FakeWS:
            def __init__(self):
                self._workspaces = {"ws1": FakeItem(), "ws2": FakeItem()}
        c = PersonalMetricsCollector()
        c.set_workspace_manager(FakeWS())
        m = await c.collect()
        assert m.artifacts_generated == 4

    @pytest.mark.asyncio
    async def test_collect_success_rate(self):
        today = datetime.now(timezone.utc).isoformat()
        class FakeStore:
            async def list_tasks(self):
                return [
                    {"task_id": "t1", "created_at": today, "status": "completed"},
                    {"task_id": "t2", "created_at": today, "status": "completed"},
                    {"task_id": "t3", "created_at": today, "status": "failed"},
                ]
        c = PersonalMetricsCollector()
        c.set_task_store(FakeStore())
        m = await c.collect()
        assert m.success_rate == pytest.approx(2 / 3, abs=0.01)

    @pytest.mark.asyncio
    async def test_collect_handles_exceptions(self):
        class BadStore:
            async def list_tasks(self):
                raise RuntimeError("boom")
        c = PersonalMetricsCollector()
        c.set_task_store(BadStore())
        m = await c.collect()
        assert m.tasks_today == 0

    @pytest.mark.asyncio
    async def test_singleton_collector(self):
        from app.analytics.metrics import get_personal_metrics_collector
        c1 = get_personal_metrics_collector()
        c2 = get_personal_metrics_collector()
        assert c1 is c2

class TestInsight:
    def test_insight_basic(self):
        i = Insight(type="tip", title="Test", message="Hello")
        assert i.type == "tip"
        assert i.title == "Test"
        assert i.priority == 0

    def test_insight_to_dict(self):
        i = Insight(type="warning", title="Warn", message="Careful", priority=2, action="review")
        d = i.to_dict()
        assert d["type"] == "warning"
        assert d["title"] == "Warn"
        assert d["priority"] == 2
        assert d["action"] == "review"


class TestAIInsightGenerator:
    def test_generate_empty(self):
        gen = AIInsightGenerator()
        m = PersonalMetrics()
        insights = gen.generate(m)
        assert len(insights) >= 1
        tip_types = [i.type for i in insights]
        assert "tip" in tip_types

    def test_generate_high_success(self):
        gen = AIInsightGenerator()
        m = PersonalMetrics(tasks_completed_today=5, success_rate=0.9)
        insights = gen.generate(m)
        types = [i.type for i in insights]
        assert "achievement" in types

    def test_generate_with_failures(self):
        gen = AIInsightGenerator()
        m = PersonalMetrics(tasks_failed_today=3, tasks_completed_today=1)
        insights = gen.generate(m)
        types = [i.type for i in insights]
        assert "warning" in types

    def test_generate_idle_agents(self):
        gen = AIInsightGenerator()
        m = PersonalMetrics(agents_total=3, agents_active=0)
        insights = gen.generate(m)
        types = [i.type for i in insights]
        assert "tip" in types

    def test_generate_knowledge_suggestion(self):
        gen = AIInsightGenerator()
        m = PersonalMetrics(tasks_completed_today=4, knowledge_items_added=0)
        insights = gen.generate(m)
        types = [i.type for i in insights]
        assert "suggestion" in types

    def test_generate_active_agents(self):
        gen = AIInsightGenerator()
        m = PersonalMetrics(agent_executions_today=15)
        insights = gen.generate(m)
        types = [i.type for i in insights]
        assert "achievement" in types

    def test_insight_priority_is_set(self):
        gen = AIInsightGenerator()
        m = PersonalMetrics(tasks_failed_today=1)
        insights = gen.generate(m)
        for i in insights:
            assert isinstance(i.priority, int)

    def test_insight_action_field(self):
        gen = AIInsightGenerator()
        m = PersonalMetrics(tasks_completed_today=5, success_rate=0.95)
        insights = gen.generate(m)
        for i in insights:
            assert isinstance(i.action, str)

    def test_singleton_generator(self):
        g1 = get_insight_generator()
        g2 = get_insight_generator()
        assert g1 is g2

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestPersonalDashboardAPI:
    @pytest.mark.asyncio
    async def test_get_dashboard_returns_200(self, client):
        resp = await client.get("/api/v1/personal/dashboard")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_dashboard_has_success(self, client):
        resp = await client.get("/api/v1/personal/dashboard")
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_dashboard_has_metrics(self, client):
        resp = await client.get("/api/v1/personal/dashboard")
        data = resp.json()
        assert "metrics" in data

    @pytest.mark.asyncio
    async def test_get_dashboard_has_insights(self, client):
        resp = await client.get("/api/v1/personal/dashboard")
        data = resp.json()
        assert "insights" in data
        assert isinstance(data["insights"], list)

    @pytest.mark.asyncio
    async def test_get_dashboard_has_daily_summary(self, client):
        resp = await client.get("/api/v1/personal/dashboard")
        data = resp.json()
        assert "daily_summary" in data
        assert "text" in data["daily_summary"]
        assert "mood" in data["daily_summary"]

    @pytest.mark.asyncio
    async def test_dashboard_insight_structure(self, client):
        resp = await client.get("/api/v1/personal/dashboard")
        data = resp.json()
        for insight in data["insights"]:
            assert "type" in insight
            assert "title" in insight
            assert "message" in insight

    @pytest.mark.asyncio
    async def test_dashboard_metrics_structure(self, client):
        resp = await client.get("/api/v1/personal/dashboard")
        data = resp.json()
        m = data["metrics"]
        assert "efficiency" in m
        assert "knowledge_growth" in m
        assert "agent_activity" in m

    @pytest.mark.asyncio
    async def test_dashboard_summary_mood(self, client):
        resp = await client.get("/api/v1/personal/dashboard")
        data = resp.json()
        assert data["daily_summary"]["mood"] in ["productive", "idle"]

    @pytest.mark.asyncio
    async def test_response_fast(self, client):
        import time
        start = time.time()
        await client.get("/api/v1/personal/dashboard")
        elapsed = time.time() - start
        assert elapsed < 5.0

class TestPersonalMetricsExtra:
    def test_generated_at_is_iso_format(self):
        m = PersonalMetrics()
        assert "T" in m.generated_at

    def test_custom_values_persist(self):
        m = PersonalMetrics(tasks_today=10, tasks_running=3,
                            knowledge_items_added=7, experience_records_created=4,
                            artifacts_generated=12, agents_active=1, agents_total=5,
                            agent_executions_today=20)
        d = m.to_dict()
        assert d["tasks_today"] == 10
        assert d["tasks_running"] == 3
        assert d["knowledge_growth"]["artifacts_generated"] == 12
        assert d["agent_activity"]["agent_executions_today"] == 20

    def test_success_rate_zero_by_default(self):
        m = PersonalMetrics()
        assert m.success_rate == 0.0

    def test_average_duration_default_zero(self):
        m = PersonalMetrics()
        assert m.average_duration_ms == 0.0

    def test_total_iterations_default_zero(self):
        m = PersonalMetrics()
        assert m.total_iterations == 0
