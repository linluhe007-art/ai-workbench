"""Phase Beta-Search tests - Information Extractor"""
import pytest
from app.research.extractor import InformationExtractor, Document, get_extractor


class TestDocument:
    def test_create(self):
        doc = Document(source="https://x.com", title="My Title", content="Hello")
        assert doc.source == "https://x.com"
        assert doc.title == "My Title"
        assert doc.content == "Hello"

    def test_to_dict(self):
        doc = Document(source="s", title="t", content="c", content_type="markdown")
        d = doc.to_dict()
        assert d["source"] == "s"
        assert d["content_type"] == "markdown"

    def test_default_content_type(self):
        doc = Document(source="s", title="t", content="c")
        assert doc.content_type == "text"


class TestInformationExtractor:
    def test_extract_html_strips_tags(self):
        ext = InformationExtractor()
        doc = ext.extract("<html><body><p>Hello World</p></body></html>", "http://x.com", "html")
        assert "Hello World" in doc.content
        assert "<p>" not in doc.content

    def test_extract_html_removes_scripts(self):
        ext = InformationExtractor()
        doc = ext.extract("<html><script>alert(1)</script><p>Content</p></html>", "http://x.com", "html")
        assert "Content" in doc.content
        assert "alert" not in doc.content

    def test_extract_markdown_preserves_format(self):
        ext = InformationExtractor()
        md = "# Title\n\n## Section\nContent here"
        doc = ext.extract(md, "http://x.com", "markdown")
        assert "# Title" in doc.content
        assert doc.content_type == "markdown"

    def test_extract_json_parses(self):
        ext = InformationExtractor()
        doc = ext.extract('{"title": "My JSON", "data": [1,2,3]}', "http://x.com", "json")
        assert doc.content_type == "json"
        assert "My JSON" in doc.content or doc.title == "My JSON"

    def test_extract_text_cleans(self):
        ext = InformationExtractor()
        doc = ext.extract("   Hello   \n\n\nWorld   ", "http://x.com", "text")
        assert "Hello" in doc.content
        assert "World" in doc.content

    def test_extract_unknown_type_falls_back(self):
        ext = InformationExtractor()
        doc = ext.extract("Some content", "http://x.com", "unknown")
        assert doc.content_type == "text"
        assert "Some content" in doc.content

    def test_strip_html_complex(self):
        ext = InformationExtractor()
        html = "<html><head><style>.x{color:red}</style></head><body><div>Keep this</div><script>ignore</script></body></html>"
        doc = ext.extract(html, "http://x.com", "html")
        assert "Keep this" in doc.content
        assert ".x{color:red}" not in doc.content

    def test_extract_rss(self):
        ext = InformationExtractor()
        rss = "<rss><channel><item><title>News</title><description>Description text</description></item></channel></rss>"
        doc = ext.extract(rss, "http://x.com", "rss")
        assert "News" in doc.content or "Description" in doc.content

    def test_clean_text_collapses_whitespace(self):
        ext = InformationExtractor()
        doc = ext.extract("a    b\n\n\nc", "http://x.com", "text")
        assert "a b" in doc.content
        assert "c" in doc.content


class TestGetExtractor:
    def test_singleton(self):
        e1 = get_extractor()
        e2 = get_extractor()
        assert e1 is e2
