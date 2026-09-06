"""Phase 5.11 tests - AI Usage Metrics"""
import pytest
from app.analytics.ai_metrics import AIUsageRecord, AIUsageTracker, get_ai_usage_tracker
from httpx import AsyncClient, ASGITransport
from app.main import app


class TestAIUsageRecord:
    def test_default(self):
        r = AIUsageRecord()
        assert r.id != ""
        assert r.model == ""

    def test_to_dict(self):
        r = AIUsageRecord(model="llama3", provider="ollama", tokens_input=100, tokens_output=50, latency_ms=250.5, cost=0.001, task_id="t1")
        d = r.to_dict()
        assert d["model"] == "llama3"
        assert d["tokens_input"] == 100
        assert d["latency_ms"] == 250.5


class TestAIUsageTracker:
    def test_record_single(self):
        t = AIUsageTracker()
        t.record("llama3", "ollama", 10, 5)
        assert len(t.get_records()) == 1

    def test_record_multiple(self):
        t = AIUsageTracker()
        for i in range(5):
            t.record(f"model{i}", "ollama", 10, 5)
        assert len(t.get_records()) == 5

    def test_get_summary(self):
        t = AIUsageTracker()
        t.record("llama3", "ollama", 100, 50)
        t.record("mistral", "ollama", 200, 100)
        s = t.get_summary()
        assert s["total_tokens_input"] == 300
        assert s["total_tokens_output"] == 150
        assert s["total_records"] == 2

    def test_get_summary_cost(self):
        t = AIUsageTracker()
        t.record("gpt4", "openai", 100, 50, cost=0.01)
        t.record("gpt4", "openai", 100, 50, cost=0.02)
        s = t.get_summary()
        assert s["total_cost"] == pytest.approx(0.03, abs=0.001)

    def test_get_summary_latency(self):
        t = AIUsageTracker()
        t.record("gpt4", "openai", 10, 5, latency_ms=100)
        t.record("gpt4", "openai", 10, 5, latency_ms=200)
        s = t.get_summary()
        assert s["average_latency_ms"] == 150.0

    def test_get_summary_model_usage(self):
        t = AIUsageTracker()
        t.record("llama3", "ollama", 10, 5)
        t.record("llama3", "ollama", 10, 5)
        t.record("mistral", "ollama", 10, 5)
        s = t.get_summary()
        assert s["model_usage"]["llama3"] == 2
        assert s["model_usage"]["mistral"] == 1

    def test_get_records_limit(self):
        t = AIUsageTracker()
        for i in range(10):
            t.record("m", "p", 1, 1)
        assert len(t.get_records(limit=3)) == 3

    def test_get_records_offset(self):
        t = AIUsageTracker()
        for i in range(5):
            t.record("m", "p", i, i)
        assert len(t.get_records(limit=2, offset=3)) == 2

    def test_clear(self):
        t = AIUsageTracker()
        t.record("m", "p", 1, 1)
        t.clear()
        assert len(t.get_records()) == 0

    def test_empty_summary(self):
        t = AIUsageTracker()
        s = t.get_summary()
        assert s["total_records"] == 0
        assert s["total_tokens"] == 0

    def test_record_with_all_fields(self):
        t = AIUsageTracker()
        t.record("gpt4", "openai", 100, 50, latency_ms=300, cost=0.005, task_id="t1", agent_id="a1")
        r = t.get_records()[0]
        assert r["task_id"] == "t1"
        assert r["agent_id"] == "a1"

    def test_singleton(self):
        t1 = get_ai_usage_tracker()
        t2 = get_ai_usage_tracker()
        assert t1 is t2

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestAIUsageAPI:
    @pytest.mark.asyncio
    async def test_get_usage_200(self, client):
        resp = await client.get("/api/v1/analytics/ai-usage")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_usage_structure(self, client):
        resp = await client.get("/api/v1/analytics/ai-usage")
        data = resp.json()
        assert data["success"] is True
        assert "records" in data

    @pytest.mark.asyncio
    async def test_get_summary_200(self, client):
        resp = await client.get("/api/v1/analytics/ai-summary")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_summary_structure(self, client):
        resp = await client.get("/api/v1/analytics/ai-summary")
        data = resp.json()
        assert data["success"] is True
        assert "summary" in data
        assert "total_tokens" in data["summary"]

    @pytest.mark.asyncio
    async def test_get_usage_with_params(self, client):
        resp = await client.get("/api/v1/analytics/ai-usage?limit=10&offset=5")
        assert resp.status_code == 200


class TestAIUsageExtra:
    def test_record_cost_float(self):
        r = AIUsageRecord(cost=0.00345)
        d = r.to_dict()
        assert d["cost"] == 0.00345

    def test_record_token_fields(self):
        t = AIUsageTracker()
        t.record("m", "p", 500, 300)
        s = t.get_summary()
        assert s["total_tokens"] == 800

    def test_get_summary_no_latency(self):
        t = AIUsageTracker()
        t.record("m", "p", 1, 1)
        s = t.get_summary()
        assert s["average_latency_ms"] == 0

    def test_multiple_providers(self):
        t = AIUsageTracker()
        t.record("m1", "ollama", 10, 5)
        t.record("m2", "openai", 20, 10)
        s = t.get_summary()
        assert s["total_records"] == 2

    def test_record_created_at(self):
        r = AIUsageRecord()
        assert "T" in r.created_at

    def test_summary_model_usage_empty(self):
        t = AIUsageTracker()
        s = t.get_summary()
        assert s["model_usage"] == {}

class TestAIUsageExtra2:
    def test_record_id_unique(self):
        r1 = AIUsageRecord()
        r2 = AIUsageRecord()
        assert r1.id != r2.id

    def test_records_sorted_by_time(self):
        t = AIUsageTracker()
        t.record("a", "p", 1, 1)
        t.record("b", "p", 1, 1)
        recs = t.get_records()
        assert len(recs) == 2

    def test_large_token_count(self):
        t = AIUsageTracker()
        t.record("m", "p", 100000, 50000)
        s = t.get_summary()
        assert s["total_tokens"] == 150000

    def test_zero_cost_default(self):
        r = AIUsageRecord()
        assert r.cost == 0.0

    def test_latency_ms_default(self):
        r = AIUsageRecord()
        assert r.latency_ms == 0.0
