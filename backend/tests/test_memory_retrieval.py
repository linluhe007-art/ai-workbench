"""
Phase 3.14 测试 — MemoryRetriever
覆盖：
- 关键词匹配
- 成功率排序
- 时间衰减
- 组合排序
- 空查询
- 来源适配
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.memory.retrieval import MemoryRetriever, RetrievalResult


class TestKeywordMatching:

    def test_exact_match(self):
        r = MemoryRetriever()
        items = [{"text": "研究AI趋势", "source": "test"}]
        results = r.retrieve("研究AI趋势", items)
        assert len(results) == 1
        assert results[0].score > 0

    def test_partial_match(self):
        r = MemoryRetriever()
        items = [{"text": "研究AI趋势并写报告", "source": "test"}]
        results = r.retrieve("研究AI", items)
        assert len(results) == 1

    def test_word_match(self):
        r = MemoryRetriever()
        items = [{"text": "研究 报告 趋势", "source": "test"}]
        results = r.retrieve("研究 趋势", items)
        assert len(results) == 1

    def test_no_match(self):
        r = MemoryRetriever()
        items = [{"text": "烹饪美食", "source": "test"}]
        results = r.retrieve("研究AI", items)
        assert len(results) == 0


class TestSuccessScore:

    def test_success_higher_than_failure(self):
        r = MemoryRetriever(success_weight=1.0, keyword_weight=0.0, decay_weight=0.0)
        items = [
            {"text": "x", "success": True, "source": "test"},
            {"text": "x", "success": False, "source": "test"},
        ]
        results = r.retrieve("x", items)
        assert results[0].item["success"] is True

    def test_no_success_field_neutral(self):
        r = MemoryRetriever(success_weight=1.0, keyword_weight=0.0, decay_weight=0.0)
        items = [{"text": "x", "source": "test"}]
        results = r.retrieve("x", items)
        assert len(results) == 1


class TestTimeDecay:

    def test_recent_higher_than_old(self):
        r = MemoryRetriever(keyword_weight=0.0, success_weight=0.0, decay_weight=1.0)
        now = datetime.now(timezone.utc)
        items = [
            {"text": "x", "created_at": (now - timedelta(hours=1)).isoformat(), "source": "test"},
            {"text": "x", "created_at": (now - timedelta(hours=48)).isoformat(), "source": "test"},
        ]
        results = r.retrieve("x", items)
        assert results[0].item["created_at"] > results[1].item["created_at"]

    def test_no_created_at_neutral(self):
        r = MemoryRetriever(decay_weight=1.0, keyword_weight=0.0, success_weight=0.0)
        items = [{"text": "x", "source": "test"}]
        results = r.retrieve("x", items)
        assert len(results) == 1

    def test_half_life_affects_decay(self):
        r_fast = MemoryRetriever(decay_half_life_hours=1.0, keyword_weight=0.0, success_weight=0.0, decay_weight=1.0)
        r_slow = MemoryRetriever(decay_half_life_hours=1000.0, keyword_weight=0.0, success_weight=0.0, decay_weight=1.0)
        now = datetime.now(timezone.utc)
        items = [{"text": "x", "created_at": (now - timedelta(hours=2)).isoformat(), "source": "test"}]

        fast = r_fast.retrieve("x", items)
        slow = r_slow.retrieve("x", items)
        assert slow[0].score > fast[0].score


class TestCombinedScoring:

    def test_limit(self):
        r = MemoryRetriever()
        items = [{"text": f"研究{i}", "source": "test"} for i in range(20)]
        results = r.retrieve("研究", items, limit=5)
        assert len(results) == 5

    def test_empty_query(self):
        r = MemoryRetriever()
        results = r.retrieve("", [{"text": "x", "source": "test"}])
        assert len(results) == 0

    def test_empty_items(self):
        r = MemoryRetriever()
        results = r.retrieve("query", [])
        assert len(results) == 0

    def test_result_is_retrieval_result(self):
        r = MemoryRetriever()
        items = [{"text": "研究AI", "source": "test", "success": True}]
        results = r.retrieve("研究", items)
        assert isinstance(results[0], RetrievalResult)
        assert results[0].score > 0


class TestSourceAdapters:

    def test_retrieve_from_experiences(self):
        r = MemoryRetriever()
        records = [
            {"task_pattern": "研究AI趋势", "agents": ["a"], "success": True, "created_at": datetime.now(timezone.utc).isoformat()},
            {"task_pattern": "写技术报告", "agents": ["b"], "success": False, "created_at": datetime.now(timezone.utc).isoformat()},
        ]
        results = r.retrieve_from_experiences("研究", records)
        assert len(results) >= 1
        assert results[0].source == "experience"

    def test_retrieve_from_agent_events(self):
        r = MemoryRetriever()
        events = [
            {"content": "研究AI趋势的结果", "event_type": "task", "created_at": datetime.now(timezone.utc).isoformat()},
            {"content": "写报告完成", "event_type": "task", "created_at": datetime.now(timezone.utc).isoformat()},
        ]
        results = r.retrieve_from_agent_events("研究", events)
        assert len(results) >= 1
        assert results[0].source == "agent_memory"