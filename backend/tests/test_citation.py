"""Phase Beta-Search tests - Citation System"""
import pytest
from app.research.citation import Citation, CitationManager, get_citation_manager


class TestCitation:
    def test_create(self):
        c = Citation(url="https://example.com", title="Example")
        assert c.url == "https://example.com"
        assert c.title == "Example"
        assert c.source_type == "web"

    def test_content_hash_generated(self):
        c = Citation(url="https://example.com/page", title="Page")
        assert len(c.content_hash) == 12

    def test_to_dict(self):
        c = Citation(url="https://x.com", title="X Site")
        d = c.to_dict()
        assert d["url"] == "https://x.com"
        assert "access_date" in d
        assert "content_hash" in d

    def test_custom_source_type(self):
        c = Citation(url="https://x.com", title="T", source_type="academic")
        assert c.source_type == "academic"


class TestCitationManager:
    def test_record_single(self):
        cm = CitationManager()
        c = Citation(url="https://a.com", title="A")
        cm.record("task-1", c)
        assert cm.get_citation_count("task-1") == 1

    def test_record_batch(self):
        cm = CitationManager()
        citations = [
            Citation(url="https://a.com", title="A"),
            Citation(url="https://b.com", title="B"),
            Citation(url="https://c.com", title="C"),
        ]
        cm.record_batch("task-2", citations)
        assert cm.get_citation_count("task-2") == 3

    def test_get_citations(self):
        cm = CitationManager()
        cm.record("task-3", Citation(url="https://x.com", title="X"))
        result = cm.get_citations("task-3")
        assert len(result) == 1
        assert result[0]["title"] == "X"

    def test_clear(self):
        cm = CitationManager()
        cm.record("task-4", Citation(url="https://d.com", title="D"))
        cm.clear("task-4")
        assert cm.get_citation_count("task-4") == 0

    def test_task_isolation(self):
        cm = CitationManager()
        cm.record("t1", Citation(url="https://a.com", title="A"))
        cm.record("t2", Citation(url="https://b.com", title="B"))
        assert cm.get_citation_count("t1") == 1
        assert cm.get_citation_count("t2") == 1

    def test_create_citation_from_source(self):
        cm = CitationManager()
        c = cm.create_citation_from_source("My Source", "https://mysource.com", "blog")
        assert c.title == "My Source"
        assert c.source_type == "blog"
        assert c.url == "https://mysource.com"


class TestGetCitationManager:
    def test_singleton(self):
        cm1 = get_citation_manager()
        cm2 = get_citation_manager()
        assert cm1 is cm2
