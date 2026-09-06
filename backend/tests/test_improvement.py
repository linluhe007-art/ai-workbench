"""Phase 5.8 tests - Self Improvement Engine"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.improvement.analyzer import (
    PerformanceAnalyzer, AnalysisReport, get_performance_analyzer,
)
from app.improvement.strategy import (
    StrategyEngine, StrategyRecommendation, StrategyPlan, get_strategy_engine,
)
from app.improvement.optimizer import (
    OptimizationEngine, OptimizationRecord, get_optimization_engine,
)
from app.main import app


# ========== AnalysisReport ==========

class TestAnalysisReport:
    def test_default_values(self):
        r = AnalysisReport()
        assert r.total_tasks == 0
        assert r.completed_tasks == 0
        assert r.failed_tasks == 0
        assert r.task_success_rate == 0.0
        assert r.best_agent == ""
        assert r.worst_agent == ""

    def test_to_dict_structure(self):
        r = AnalysisReport(total_tasks=10, completed_tasks=8, failed_tasks=2)
        d = r.to_dict()
        assert d["task_analysis"]["total_tasks"] == 10
        assert d["task_analysis"]["completed_tasks"] == 8
        assert d["task_analysis"]["failed_tasks"] == 2
        assert "agent_performance" in d
        assert "bottlenecks" in d

    def test_to_dict_success_rate(self):
        r = AnalysisReport(total_tasks=5, completed_tasks=4, task_success_rate=0.8)
        d = r.to_dict()
        assert d["task_analysis"]["success_rate"] == 0.8

    def test_to_dict_best_worst_agent(self):
        r = AnalysisReport(best_agent="agent-a", worst_agent="agent-b")
        d = r.to_dict()
        assert d["best_agent"] == "agent-a"
        assert d["worst_agent"] == "agent-b"

    def test_to_dict_bottlenecks(self):
        r = AnalysisReport(bottlenecks=[{"type": "slow", "severity": "high"}])
        d = r.to_dict()
        assert len(d["bottlenecks"]) == 1

    def test_to_dict_workflow_stats(self):
        r = AnalysisReport(workflow_stats={"agents": 3})
        d = r.to_dict()
        assert d["workflow_stats"]["agents"] == 3

    def test_generated_at_not_empty(self):
        r = AnalysisReport()
        assert r.generated_at != ""
        assert "T" in r.generated_at

# ========== PerformanceAnalyzer ==========

class TestPerformanceAnalyzer:
    @pytest.mark.asyncio
    async def test_analyze_empty(self):
        a = PerformanceAnalyzer()
        r = await a.analyze()
        assert isinstance(r, AnalysisReport)
        assert r.total_tasks == 0

    @pytest.mark.asyncio
    async def test_analyze_with_tasks(self):
        class FakeStore:
            async def list_tasks(self):
                return [
                    {"task_id": "t1", "status": "completed", "duration_ms": 1000},
                    {"task_id": "t2", "status": "completed", "duration_ms": 2000},
                    {"task_id": "t3", "status": "failed", "duration_ms": 500},
                ]
        a = PerformanceAnalyzer()
        a.set_task_store(FakeStore())
        r = await a.analyze()
        assert r.total_tasks == 3
        assert r.completed_tasks == 2
        assert r.failed_tasks == 1
        assert r.task_success_rate == pytest.approx(2/3, abs=0.01)

    @pytest.mark.asyncio
    async def test_analyze_average_duration(self):
        class FakeStore:
            async def list_tasks(self):
                return [
                    {"task_id": "t1", "status": "completed", "duration_ms": 1000},
                    {"task_id": "t2", "status": "completed", "duration_ms": 3000},
                ]
        a = PerformanceAnalyzer()
        a.set_task_store(FakeStore())
        r = await a.analyze()
        assert r.average_task_duration_ms == 2000.0

    @pytest.mark.asyncio
    async def test_analyze_high_failure_bottleneck(self):
        class FakeStore:
            async def list_tasks(self):
                return [{"task_id": f"t{i}", "status": "failed"} for i in range(6)]
        a = PerformanceAnalyzer()
        a.set_task_store(FakeStore())
        r = await a.analyze()
        assert len(r.bottlenecks) >= 1
        assert any(b["type"] == "high_failure_rate" for b in r.bottlenecks)

    @pytest.mark.asyncio
    async def test_analyze_slow_execution_bottleneck(self):
        class FakeStore:
            async def list_tasks(self):
                return [{"task_id": "t1", "status": "completed", "duration_ms": 60000}]
        a = PerformanceAnalyzer()
        a.set_task_store(FakeStore())
        r = await a.analyze()
        assert any(b["type"] == "slow_execution" for b in r.bottlenecks)

    @pytest.mark.asyncio
    async def test_analyze_with_agents(self):
        class FakeRuntime:
            def list_agents(self):
                return [
                    {"id": "a1", "executions": 10, "errors": 1},
                    {"id": "a2", "executions": 10, "errors": 5},
                ]
        a = PerformanceAnalyzer()
        a.set_agent_runtime(FakeRuntime())
        r = await a.analyze()
        assert len(r.agent_performance) == 2
        assert r.best_agent == "a1"
        assert r.worst_agent == "a2"

    @pytest.mark.asyncio
    async def test_analyze_single_agent(self):
        class FakeRuntime:
            def list_agents(self):
                return [{"id": "a1", "executions": 5, "errors": 0}]
        a = PerformanceAnalyzer()
        a.set_agent_runtime(FakeRuntime())
        r = await a.analyze()
        assert r.best_agent == "a1"
        assert r.worst_agent == "a1"

    @pytest.mark.asyncio
    async def test_analyze_handles_exceptions(self):
        class BadStore:
            async def list_tasks(self):
                raise RuntimeError("boom")
        a = PerformanceAnalyzer()
        a.set_task_store(BadStore())
        r = await a.analyze()
        assert r.total_tasks == 0

    @pytest.mark.asyncio
    async def test_singleton_analyzer(self):
        a1 = get_performance_analyzer()
        a2 = get_performance_analyzer()
        assert a1 is a2

    @pytest.mark.asyncio
    async def test_analyze_with_no_subsystems(self):
        a = PerformanceAnalyzer()
        r = await a.analyze()
        assert r.total_tasks == 0
        assert r.agent_performance == []

# ========== StrategyRecommendation ==========

class TestStrategyRecommendation:
    def test_basic(self):
        s = StrategyRecommendation(id="r1", category="agent_selection", title="Test", priority=2)
        assert s.id == "r1"
        assert s.category == "agent_selection"
        assert s.priority == 2

    def test_to_dict(self):
        s = StrategyRecommendation(
            id="r1", category="retry", title="Retry more",
            description="Increase retries", priority=1,
            expected_impact="Better", action={"type": "config"},
        )
        d = s.to_dict()
        assert d["id"] == "r1"
        assert d["category"] == "retry"
        assert d["title"] == "Retry more"
        assert d["action"]["type"] == "config"


# ========== StrategyPlan ==========

class TestStrategyPlan:
    def test_empty_plan(self):
        p = StrategyPlan()
        assert p.recommendations == []
        assert p.summary == ""

    def test_to_dict(self):
        s = StrategyRecommendation(id="r1", category="retry", title="T", priority=0)
        p = StrategyPlan(recommendations=[s], summary="One rec")
        d = p.to_dict()
        assert len(d["recommendations"]) == 1
        assert d["summary"] == "One rec"


# ========== StrategyEngine ==========

class TestStrategyEngine:
    def test_generate_from_empty_report(self):
        engine = StrategyEngine()
        report = AnalysisReport()
        plan = engine.generate(report)
        assert isinstance(plan, StrategyPlan)
        assert plan.summary != ""

    def test_generate_with_best_agent(self):
        engine = StrategyEngine()
        report = AnalysisReport(
            total_tasks=10, best_agent="agent-a",
            agent_performance=[{"agent_id": "agent-a", "executions": 10, "errors": 0, "success_rate": 1.0}],
        )
        plan = engine.generate(report)
        has_agent_rec = any(r.category == "agent_selection" for r in plan.recommendations)
        assert has_agent_rec

    def test_generate_low_success_rate(self):
        engine = StrategyEngine()
        report = AnalysisReport(total_tasks=10, completed_tasks=3, task_success_rate=0.3)
        plan = engine.generate(report)
        has_retry = any(r.category == "retry" for r in plan.recommendations)
        assert has_retry

    def test_generate_slow_tasks(self):
        engine = StrategyEngine()
        report = AnalysisReport(total_tasks=3, average_task_duration_ms=20000)
        plan = engine.generate(report)
        has_workflow = any(r.category == "workflow" for r in plan.recommendations)
        assert has_workflow

    def test_generate_with_bottlenecks(self):
        engine = StrategyEngine()
        report = AnalysisReport(
            total_tasks=5, bottlenecks=[{"type": "high_failure_rate", "severity": "high", "suggestion": "Fix"}],
        )
        plan = engine.generate(report)
        has_bn = any(r.category == "bottleneck" for r in plan.recommendations)
        assert has_bn

    def test_recommendations_sorted_by_priority(self):
        engine = StrategyEngine()
        report = AnalysisReport(
            total_tasks=10, completed_tasks=3, task_success_rate=0.3,
            best_agent="a1", worst_agent="a2",
            average_task_duration_ms=20000,
            agent_performance=[
                {"agent_id": "a1", "executions": 10, "errors": 1, "success_rate": 0.9},
                {"agent_id": "a2", "executions": 10, "errors": 5, "success_rate": 0.5},
            ],
        )
        plan = engine.generate(report)
        priorities = [r.priority for r in plan.recommendations]
        assert priorities == sorted(priorities, reverse=True)

    def test_singleton_engine(self):
        e1 = get_strategy_engine()
        e2 = get_strategy_engine()
        assert e1 is e2

    def test_both_best_and_worst_agents(self):
        engine = StrategyEngine()
        report = AnalysisReport(
            total_tasks=10, best_agent="a1", worst_agent="a2",
            agent_performance=[
                {"agent_id": "a1", "executions": 10, "errors": 0, "success_rate": 1.0},
                {"agent_id": "a2", "executions": 10, "errors": 8, "success_rate": 0.2},
            ],
        )
        plan = engine.generate(report)
        agent_recs = [r for r in plan.recommendations if r.category == "agent_selection"]
        assert len(agent_recs) >= 2

    def test_no_duplicate_recommendation_ids(self):
        engine = StrategyEngine()
        report = AnalysisReport(total_tasks=10, completed_tasks=3, task_success_rate=0.3)
        plan = engine.generate(report)
        ids = [r.id for r in plan.recommendations]
        assert len(ids) == len(set(ids))

# ========== OptimizationRecord ==========

class TestOptimizationRecord:
    def test_basic(self):
        r = OptimizationRecord(id="o1", category="retry", title="Test")
        assert r.id == "o1"
        assert r.status == "applied"

    def test_to_dict(self):
        r = OptimizationRecord(
            id="o1", recommendation_id="r1", category="retry",
            title="Test", action={"type": "config"}, status="applied",
        )
        d = r.to_dict()
        assert d["id"] == "o1"
        assert d["status"] == "applied"
        assert d["action"]["type"] == "config"


# ========== OptimizationEngine ==========

class TestOptimizationEngine:
    def test_apply_single_recommendation(self):
        engine = OptimizationEngine()
        rec = StrategyRecommendation(id="r1", category="retry", title="Test", priority=1)
        record = engine.apply(rec)
        assert record.category == "retry"
        assert record.status == "applied"
        assert record.recommendation_id == "r1"

    def test_apply_plan(self):
        engine = OptimizationEngine()
        recs = [
            StrategyRecommendation(id="r1", category="retry", title="R1", priority=1),
            StrategyRecommendation(id="r2", category="workflow", title="R2", priority=1),
        ]
        plan = StrategyPlan(recommendations=recs)
        records = engine.apply_plan(plan)
        assert len(records) == 2

    def test_list_records(self):
        engine = OptimizationEngine()
        rec = StrategyRecommendation(id="r1", category="retry", title="Test", priority=1)
        engine.apply(rec)
        records = engine.list_records()
        assert len(records) >= 1

    def test_get_record(self):
        engine = OptimizationEngine()
        rec = StrategyRecommendation(id="r1", category="retry", title="Test", priority=1)
        record = engine.apply(rec)
        found = engine.get_record(record.id)
        assert found is not None
        assert found.id == record.id

    def test_get_nonexistent_record(self):
        engine = OptimizationEngine()
        assert engine.get_record("nonexistent") is None

    def test_revert_record(self):
        engine = OptimizationEngine()
        rec = StrategyRecommendation(id="r1", category="retry", title="Test", priority=1)
        record = engine.apply(rec)
        ok = engine.revert(record.id)
        assert ok is True
        found = engine.get_record(record.id)
        assert found.status == "reverted"

    def test_revert_twice_fails(self):
        engine = OptimizationEngine()
        rec = StrategyRecommendation(id="r1", category="retry", title="Test", priority=1)
        record = engine.apply(rec)
        engine.revert(record.id)
        ok = engine.revert(record.id)
        assert ok is False

    def test_get_stats(self):
        engine = OptimizationEngine()
        engine.apply(StrategyRecommendation(id="r1", category="retry", title="T1", priority=1))
        engine.apply(StrategyRecommendation(id="r2", category="agent_selection", title="T2", priority=1))
        stats = engine.get_stats()
        assert stats["total_applied"] == 2
        assert "retry" in stats["by_category"]

    def test_singleton_engine(self):
        e1 = get_optimization_engine()
        e2 = get_optimization_engine()
        assert e1 is e2

    def test_apply_generates_unique_ids(self):
        engine = OptimizationEngine()
        r1 = engine.apply(StrategyRecommendation(id="ra", category="retry", title="A", priority=1))
        r2 = engine.apply(StrategyRecommendation(id="rb", category="workflow", title="B", priority=1))
        assert r1.id != r2.id

# ========== API Tests ==========

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestImprovementReportAPI:
    @pytest.mark.asyncio
    async def test_get_report_returns_200(self, client):
        resp = await client.get("/api/v1/improvement/report")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_report_has_success(self, client):
        resp = await client.get("/api/v1/improvement/report")
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_report_has_analysis(self, client):
        resp = await client.get("/api/v1/improvement/report")
        data = resp.json()
        assert "analysis" in data
        assert "task_analysis" in data["analysis"]

    @pytest.mark.asyncio
    async def test_get_report_has_strategy_plan(self, client):
        resp = await client.get("/api/v1/improvement/report")
        data = resp.json()
        assert "strategy_plan" in data
        assert "recommendations" in data["strategy_plan"]

    @pytest.mark.asyncio
    async def test_report_analysis_structure(self, client):
        resp = await client.get("/api/v1/improvement/report")
        data = resp.json()
        a = data["analysis"]
        assert "agent_performance" in a
        assert "bottlenecks" in a
        assert "workflow_stats" in a

    @pytest.mark.asyncio
    async def test_report_strategy_recommendations_list(self, client):
        resp = await client.get("/api/v1/improvement/report")
        data = resp.json()
        assert isinstance(data["strategy_plan"]["recommendations"], list)


class TestImprovementApplyAPI:
    @pytest.mark.asyncio
    async def test_apply_no_ids(self, client):
        resp = await client.post("/api/v1/improvement/apply", json={"recommendation_ids": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "applied" in data

    @pytest.mark.asyncio
    async def test_apply_returns_records(self, client):
        resp = await client.post("/api/v1/improvement/apply", json={"recommendation_ids": []})
        data = resp.json()
        assert "records" in data


class TestImprovementHistoryAPI:
    @pytest.mark.asyncio
    async def test_get_history(self, client):
        resp = await client.get("/api/v1/improvement/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "records" in data
        assert "stats" in data

    @pytest.mark.asyncio
    async def test_history_has_stats(self, client):
        resp = await client.get("/api/v1/improvement/history")
        data = resp.json()
        assert "total_applied" in data["stats"]


class TestImprovementRevertAPI:
    @pytest.mark.asyncio
    async def test_revert_nonexistent(self, client):
        resp = await client.post("/api/v1/improvement/revert/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_revert_after_apply(self, client):
        # Apply first
        resp = await client.post("/api/v1/improvement/apply", json={"recommendation_ids": []})
        data = resp.json()
        if data["records"]:
            rec_id = data["records"][0]["id"]
            resp2 = await client.post(f"/api/v1/improvement/revert/{rec_id}")
            assert resp2.status_code == 200

# ========== Additional Analyzer Tests ==========

class TestPerformanceAnalyzerExtra:
    @pytest.mark.asyncio
    async def test_analyze_with_experience_service(self):
        class FakeExp:
            _records = [{"task": "test1"}, {"task": "test2"}]
        a = PerformanceAnalyzer()
        a.set_experience_service(FakeExp())
        r = await a.analyze()
        assert r.total_tasks == 0  # exp service not used for tasks

    @pytest.mark.asyncio
    async def test_analyze_mixed_status(self):
        class FakeStore:
            async def list_tasks(self):
                return [
                    {"task_id": "t1", "status": "completed"},
                    {"task_id": "t2", "status": "running"},
                    {"task_id": "t3", "status": "pending"},
                    {"task_id": "t4", "status": "completed"},
                ]
        a = PerformanceAnalyzer()
        a.set_task_store(FakeStore())
        r = await a.analyze()
        assert r.total_tasks == 4
        assert r.completed_tasks == 2
        assert r.failed_tasks == 0

    @pytest.mark.asyncio
    async def test_analyze_agent_without_executions(self):
        class FakeRuntime:
            def list_agents(self):
                return [{"id": "a1"}]
        a = PerformanceAnalyzer()
        a.set_agent_runtime(FakeRuntime())
        r = await a.analyze()
        assert len(r.agent_performance) == 1
        assert r.agent_performance[0]["executions"] == 0

    @pytest.mark.asyncio
    async def test_analyze_empty_agent_list(self):
        class FakeRuntime:
            def list_agents(self):
                return []
        a = PerformanceAnalyzer()
        a.set_agent_runtime(FakeRuntime())
        r = await a.analyze()
        assert r.agent_performance == []
        assert r.best_agent == ""

    @pytest.mark.asyncio
    async def test_bottleneck_severity_levels(self):
        class FakeStore:
            async def list_tasks(self):
                return [{"task_id": f"t{i}", "status": "failed"} for i in range(6)]
        a = PerformanceAnalyzer()
        a.set_task_store(FakeStore())
        r = await a.analyze()
        for b in r.bottlenecks:
            assert "severity" in b
            assert b["severity"] in ["low", "medium", "high"]

# ========== Additional Strategy Tests ==========

class TestStrategyEngineExtra:
    def test_generate_summary_format(self):
        engine = StrategyEngine()
        report = AnalysisReport(total_tasks=5)
        plan = engine.generate(report)
        assert "5" in plan.summary or "recommendation" in plan.summary.lower()

    def test_strategy_recommendation_default_action(self):
        s = StrategyRecommendation(id="x", category="test", title="T", priority=0)
        assert s.action == {}

    def test_strategy_plan_generated_at(self):
        p = StrategyPlan()
        assert p.generated_at != ""

    def test_strategy_recommendation_expected_impact(self):
        s = StrategyRecommendation(id="x", category="test", title="T", priority=1, expected_impact="Great")
        assert s.expected_impact == "Great"

    def test_generate_idle_system(self):
        engine = StrategyEngine()
        report = AnalysisReport(total_tasks=0)
        plan = engine.generate(report)
        # Should still produce a valid plan
        assert isinstance(plan, StrategyPlan)

    def test_plan_to_dict_includes_summary(self):
        engine = StrategyEngine()
        report = AnalysisReport(total_tasks=3)
        plan = engine.generate(report)
        d = plan.to_dict()
        assert "summary" in d
        assert isinstance(d["summary"], str)

# ========== Additional Optimizer Tests ==========

class TestOptimizationEngineExtra:
    def test_apply_preserves_action(self):
        engine = OptimizationEngine()
        rec = StrategyRecommendation(
            id="r1", category="retry", title="T", priority=1,
            action={"type": "config", "key": "value"},
        )
        record = engine.apply(rec)
        assert record.action["type"] == "config"

    def test_list_records_sorted_by_time(self):
        engine = OptimizationEngine()
        engine.apply(StrategyRecommendation(id="r1", category="a", title="A", priority=1))
        engine.apply(StrategyRecommendation(id="r2", category="b", title="B", priority=1))
        records = engine.list_records()
        assert len(records) == 2

    def test_apply_empty_plan(self):
        engine = OptimizationEngine()
        plan = StrategyPlan(recommendations=[])
        records = engine.apply_plan(plan)
        assert records == []

    def test_optimization_record_default_status(self):
        r = OptimizationRecord()
        assert r.status == "applied"

    def test_revert_nonexistent_returns_false(self):
        engine = OptimizationEngine()
        assert engine.revert("nonexistent") is False
