"""
Phase 4.23 tests - ExperienceEngine
Covers: record, query, stats, feedback, recommendations, search
"""
import pytest
from datetime import datetime, timezone

from app.learning.experience_engine import (
    ExperienceEngine,
    ExperienceStats,
    FeedbackRecord,
)
from app.memory.experience import ExperienceMemory


@pytest.fixture
def engine():
    mem = ExperienceMemory()
    return ExperienceEngine(mem)


class TestExperienceRecording:
    def test_record_success(self, engine):
        rec = engine.record_experience("analyze data", ["mock", "researcher"], True, 150)
        assert rec.success is True
        assert rec.task_pattern == "analyze data"
        assert "mock" in rec.agents

    def test_record_failure(self, engine):
        rec = engine.record_failure("bad task", ["mock"], "timeout error", 3000)
        assert rec.success is False
        assert rec.metadata["error"] == "timeout error"
        assert rec.metadata["failure_type"] == "execution"

    def test_record_with_metadata(self, engine):
        rec = engine.record_experience(
            "write report", ["writer"],
            True, 500, {"step_count": 3, "word_count": 1000}
        )
        assert rec.metadata["step_count"] == 3
        assert rec.metadata["word_count"] == 1000

    def test_record_feedback(self, engine):
        fb = engine.record_feedback("task-1", "analyze data", 8.5, "good")
        assert fb.rating == 8.5
        assert fb.task_id == "task-1"
        assert fb.comment == "good"

    def test_record_feedback_clamps_rating(self, engine):
        fb = engine.record_feedback("t1", "test", 15.0)
        assert fb.rating == 10.0
        fb2 = engine.record_feedback("t2", "test", -5.0)
        assert fb2.rating == 0.0


class TestExperienceQuery:
    def test_query_empty(self, engine):
        results = engine.query("nothing")
        assert results == []

    def test_query_exact_match(self, engine):
        engine.record_experience("search web", ["researcher"], True, 100)
        results = engine.query("search web")
        assert len(results) == 1
        assert results[0]["task_pattern"] == "search web"

    def test_query_partial_match(self, engine):
        engine.record_experience("search web for news", ["researcher"], True, 100)
        engine.record_experience("analyze data", ["analyst"], True, 200)
        results = engine.query("search")
        assert len(results) >= 1

    def test_query_ranks_by_success(self, engine):
        engine.record_experience("task alpha", ["a1"], True, 100)
        engine.record_experience("task alpha", ["a2"], False, 200)
        results = engine.query("task alpha")
        assert results[0]["success"] is True

    def test_query_limit(self, engine):
        for i in range(10):
            engine.record_experience(f"task {i}", ["mock"], True, 100)
        results = engine.query("task", limit=3)
        assert len(results) <= 3


class TestExperienceSearch:
    def test_search_empty(self, engine):
        results = engine.search("nothing")
        assert results == []

    def test_search_returns_scored(self, engine):
        engine.record_experience("search web for news", ["researcher"], True, 100)
        results = engine.search("search web")
        assert len(results) >= 1
        assert "score" in results[0]

    def test_search_ranks_by_relevance(self, engine):
        engine.record_experience("unrelated", ["mock"], True, 100)
        engine.record_experience("search web exactly", ["researcher"], True, 100)
        results = engine.search("search web")
        if len(results) >= 2:
            assert results[0]["score"] >= results[1]["score"]


class TestExperienceStats:
    def test_stats_empty(self, engine):
        stats = engine.get_stats()
        assert stats.total_records == 0
        assert stats.success_rate == 0.0

    def test_stats_with_records(self, engine):
        engine.record_experience("task a", ["mock"], True, 100)
        engine.record_experience("task a", ["mock"], False, 200)
        engine.record_experience("task b", ["researcher"], True, 150)
        stats = engine.get_stats()
        assert stats.total_records == 3
        assert stats.success_count == 2
        assert stats.failure_count == 1
        assert stats.success_rate == pytest.approx(2 / 3, 0.01)

    def test_stats_top_patterns(self, engine):
        for _ in range(3):
            engine.record_experience("common task", ["mock"], True, 100)
        engine.record_experience("rare task", ["mock"], True, 100)
        stats = engine.get_stats()
        assert len(stats.top_patterns) >= 1
        top = stats.top_patterns[0]
        assert top["pattern"] == "common task"
        assert top["count"] == 3

    def test_stats_top_agents(self, engine):
        engine.record_experience("task", ["good_agent"], True, 100)
        engine.record_experience("task", ["good_agent"], True, 100)
        engine.record_experience("task", ["bad_agent"], False, 100)
        stats = engine.get_stats()
        agents = {a["agent_id"]: a["success_rate"] for a in stats.top_agents}
        assert agents.get("good_agent", 0) > agents.get("bad_agent", 0)

    def test_stats_recent_failures(self, engine):
        engine.record_failure("fail task", ["mock"], "err1")
        engine.record_failure("fail task 2", ["mock"], "err2")
        stats = engine.get_stats()
        assert len(stats.recent_failures) >= 1
        assert stats.recent_failures[0]["error"] in ("err1", "err2")


class TestExperienceRecommendations:
    def test_recommendations_empty(self, engine):
        recs = engine.get_recommendations("unknown")
        assert recs["recommended_agents"] == []
        assert recs["historical_success_rate"] == 0.0

    def test_recommendations_with_history(self, engine):
        engine.record_experience("common task", ["agent_a"], True, 100)
        engine.record_experience("common task", ["agent_a"], True, 200)
        engine.record_experience("common task", ["agent_b"], False, 150)
        recs = engine.get_recommendations("common task")
        assert "agent_a" in recs["recommended_agents"]
        assert recs["historical_success_rate"] > 0

    def test_recommendations_warnings(self, engine):
        engine.record_failure("risky task", ["mock"], "timeout")
        recs = engine.get_recommendations("risky task")
        assert len(recs["warnings"]) >= 1
        assert "timeout" in recs["warnings"][0]


class TestFeedbackStats:
    def test_feedback_stats_empty(self, engine):
        stats = engine.get_feedback_stats()
        assert stats["total"] == 0
        assert stats["average_rating"] == 0.0

    def test_feedback_stats_with_data(self, engine):
        engine.record_feedback("t1", "test", 8.0)
        engine.record_feedback("t2", "test", 6.0)
        stats = engine.get_feedback_stats()
        assert stats["total"] == 2
        assert stats["average_rating"] == 7.0


class TestExperienceEngineProperties:
    def test_memory_property(self, engine):
        assert isinstance(engine.memory, ExperienceMemory)

    def test_retriever_property(self, engine):
        assert engine.retriever is not None


class TestFeedbackRecord:
    def test_feedback_record_defaults(self):
        fb = FeedbackRecord()
        assert fb.task_id == ""
        assert fb.rating == 0.0
        assert fb.comment == ""

    def test_feedback_record_fields(self):
        fb = FeedbackRecord(task_id="t1", task_pattern="test", rating=7.5, comment="ok")
        d = {"task_id": fb.task_id, "rating": fb.rating, "comment": fb.comment}
        assert d == {"task_id": "t1", "rating": 7.5, "comment": "ok"}

class TestExperienceEngineRecordFailures:
    def test_record_multiple_failures(self, engine):
        for i in range(5):
            engine.record_failure(f"task {i}", ["mock"], f"error {i}")
        stats = engine.get_stats()
        assert stats.failure_count == 5
        assert stats.success_rate == 0.0

    def test_mixed_success_failure_stats(self, engine):
        for i in range(4):
            engine.record_experience("task", ["mock"], i % 2 == 0, 100)
        stats = engine.get_stats()
        assert stats.total_records == 4
        assert 0 < stats.success_rate < 1.0


class TestExperienceEngineFeedback:
    def test_multiple_feedback(self, engine):
        engine.record_feedback("t1", "test", 5.0)
        engine.record_feedback("t2", "test", 9.0)
        engine.record_feedback("t3", "test", 7.0)
        stats = engine.get_feedback_stats()
        assert stats["total"] == 3

    def test_feedback_ratings_list(self, engine):
        engine.record_feedback("t1", "test", 4.0)
        stats = engine.get_feedback_stats()
        assert len(stats["ratings"]) == 1
        assert stats["ratings"][0]["rating"] == 4.0


class TestExperienceEngineEdgeCases:
    def test_stats_with_only_failures(self, engine):
        engine.record_failure("always fail", ["mock"], "boom")
        stats = engine.get_stats()
        assert stats.success_rate == 0.0
        assert stats.failure_count == 1

    def test_stats_with_only_successes(self, engine):
        engine.record_experience("always win", ["mock"], True, 50)
        stats = engine.get_stats()
        assert stats.success_rate == 1.0
        assert stats.success_count == 1