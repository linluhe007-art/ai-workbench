"""
Phase 3.14 测试 — ExperienceMemory
覆盖：
- 记录经验
- 查询经验
- 成功率
- 最佳 Agent
- 匹配排序
- 空查询
"""

import pytest
from app.memory.experience import ExperienceMemory


class TestExperienceRecord:

    def test_record(self):
        mem = ExperienceMemory()
        rec = mem.record_experience("研究AI", ["agent-a"], True)
        assert rec.task_pattern == "研究AI"
        assert rec.agents == ["agent-a"]
        assert rec.success is True

    def test_record_with_metadata(self):
        mem = ExperienceMemory()
        rec = mem.record_experience("写报告", ["agent-b"], False, {"duration_ms": 500})
        assert rec.metadata["duration_ms"] == 500

    def test_total_records(self):
        mem = ExperienceMemory()
        mem.record_experience("a", ["x"], True)
        mem.record_experience("b", ["y"], False)
        assert mem.total_records == 2

    def test_clear(self):
        mem = ExperienceMemory()
        mem.record_experience("a", ["x"], True)
        mem.clear()
        assert mem.total_records == 0


class TestExperienceQuery:

    def test_exact_match(self):
        mem = ExperienceMemory()
        mem.record_experience("研究AI趋势", ["agent-a"], True)
        results = mem.query_experience("研究AI趋势")
        assert len(results) == 1
        assert results[0]["task_pattern"] == "研究AI趋势"

    def test_partial_match(self):
        mem = ExperienceMemory()
        mem.record_experience("研究AI趋势并写报告", ["a"], True)
        mem.record_experience("搜索新闻", ["b"], True)
        results = mem.query_experience("研究AI")
        assert len(results) >= 1
        assert any("研究" in r["task_pattern"] for r in results)

    def test_word_match(self):
        mem = ExperienceMemory()
        mem.record_experience("研究 报告 分析", ["a"], True)
        results = mem.query_experience("研究 分析")
        assert len(results) == 1

    def test_no_match(self):
        mem = ExperienceMemory()
        mem.record_experience("研究AI", ["a"], True)
        results = mem.query_experience("烹饪美食")
        assert len(results) == 0

    def test_empty_query(self):
        mem = ExperienceMemory()
        mem.record_experience("研究", ["a"], True)
        results = mem.query_experience("")
        assert len(results) == 0

    def test_empty_memory(self):
        mem = ExperienceMemory()
        results = mem.query_experience("研究")
        assert len(results) == 0

    def test_success_prioritized(self):
        mem = ExperienceMemory()
        mem.record_experience("研究AI", ["fail-agent"], False)
        mem.record_experience("研究AI", ["ok-agent"], True)
        results = mem.query_experience("研究AI")
        assert results[0]["success"] is True

    def test_limit(self):
        mem = ExperienceMemory()
        for i in range(20):
            mem.record_experience(f"研究{i}", ["a"], True)
        results = mem.query_experience("研究", limit=5)
        assert len(results) == 5

    def test_result_fields(self):
        mem = ExperienceMemory()
        mem.record_experience("研究", ["a"], True, {"duration_ms": 100})
        results = mem.query_experience("研究")
        r = results[0]
        assert "task_pattern" in r
        assert "agents" in r
        assert "success" in r
        assert "match_score" in r
        assert "created_at" in r


class TestExperienceHelpers:

    def test_success_rate(self):
        mem = ExperienceMemory()
        mem.record_experience("研究", ["a"], True)
        mem.record_experience("研究", ["a"], True)
        mem.record_experience("研究", ["a"], False)
        rate = mem.get_success_rate("研究")
        assert abs(rate - 2 / 3) < 0.01

    def test_success_rate_no_match(self):
        mem = ExperienceMemory()
        assert mem.get_success_rate("研究") == 0.0

    def test_best_agents(self):
        mem = ExperienceMemory()
        mem.record_experience("研究", ["a"], True)
        mem.record_experience("研究", ["a"], True)
        mem.record_experience("研究", ["b"], False)
        best = mem.get_best_agents("研究")
        assert best[0] == "a"

    def test_best_agents_limit(self):
        mem = ExperienceMemory()
        for i in range(10):
            mem.record_experience("研究", [f"agent-{i}"], True)
        best = mem.get_best_agents("研究", limit=3)
        assert len(best) == 3