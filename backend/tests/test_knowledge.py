"""
Phase 5.4 tests - Knowledge Parser, Indexer, Retriever, API.
"""
import io
import pytest
from httpx import AsyncClient, ASGITransport

from app.knowledge.parser import KnowledgeParser, ParsedKnowledge, DocumentType
from app.knowledge.indexer import KnowledgeIndexer, KnowledgeDocument, KnowledgeChunk
from app.knowledge.retriever import KnowledgeRetriever
from app.main import app


class TestDocumentType:
    def test_all_types(self):
        assert DocumentType.PDF == "pdf"
        assert DocumentType.MARKDOWN == "markdown"
        assert DocumentType.TXT == "txt"
        assert DocumentType.CODE == "code"
        assert DocumentType.WEB == "web"

    def test_type_values(self):
        types = [t.value for t in DocumentType]
        assert "pdf" in types
        assert "markdown" in types


class TestKnowledgeParser:
    def test_detect_markdown(self):
        parser = KnowledgeParser()
        parsed = parser.parse("# Hello\n\ncontent", "test.md")
        assert parsed.doc_type == DocumentType.MARKDOWN

    def test_detect_code(self):
        parser = KnowledgeParser()
        parsed = parser.parse("def foo(): pass", "test.py")
        assert parsed.doc_type == DocumentType.CODE

    def test_detect_txt(self):
        parser = KnowledgeParser()
        parsed = parser.parse("plain text", "test.txt")
        assert parsed.doc_type == DocumentType.TXT

    def test_detect_pdf(self):
        parser = KnowledgeParser()
        parsed = parser.parse("dummy", "test.pdf")
        assert parsed.doc_type == DocumentType.PDF

    def test_extract_title_from_filename(self):
        parser = KnowledgeParser()
        parsed = parser.parse("content", "my_awesome_note.md")
        assert parsed.title == "my awesome note"

    def test_extract_title_from_heading(self):
        parser = KnowledgeParser()
        parsed = parser.parse("# AI Research Guide\n\ncontent")
        assert parsed.title == "AI Research Guide"

    def test_extract_title_default(self):
        parser = KnowledgeParser()
        parsed = parser.parse("", "")
        assert parsed.title == "Untitled"

    def test_chunk_content(self):
        parser = KnowledgeParser()
        long_text = "Paragraph one.\n" * 50
        parsed = parser.parse(long_text, "test.txt")
        assert len(parsed.chunks) > 1

    def test_chunk_single(self):
        parser = KnowledgeParser()
        parsed = parser.parse("short content", "test.txt")
        assert len(parsed.chunks) == 1

    def test_extract_tags_python(self):
        parser = KnowledgeParser()
        parsed = parser.parse("Using python and pandas for data analysis", "test.txt")
        assert "python" in parsed.tags

    def test_extract_tags_code(self):
        parser = KnowledgeParser()
        parsed = parser.parse("def foo(): pass", "test.py")
        assert "code" in parsed.tags

    def test_generate_summary(self):
        parser = KnowledgeParser()
        parsed = parser.parse("This is a document with enough content to generate a meaningful summary for testing purposes. " * 3, "test.txt")
        assert len(parsed.summary) > 0

    def test_html_cleaning(self):
        parser = KnowledgeParser()
        parsed = parser.parse("<html><body><p>Hello World</p><script>alert(1)</script></body></html>", "page.html")
        assert "Hello World" in parsed.content
        assert "alert" not in parsed.content

    def test_html_entity_decoding(self):
        parser = KnowledgeParser()
        parsed = parser.parse("<p>a &amp; b &lt; c</p>", "test.html")
        assert "a & b < c" in parsed.content

    def test_metadata_set(self):
        parser = KnowledgeParser()
        parsed = parser.parse("content", "file.md", "https://example.com")
        assert parsed.metadata["filename"] == "file.md"
        assert parsed.metadata["source_url"] == "https://example.com"


class TestKnowledgeIndexer:
    def test_index_content(self):
        idx = KnowledgeIndexer()
        doc = idx.index("Python async programming guide", "guide.md")
        assert doc.doc_type == "markdown"

    def test_index_creates_chunks(self):
        idx = KnowledgeIndexer()
        long_text = "Paragraph one.\n\n" * 20
        doc = idx.index(long_text, "long.md")
        assert doc.chunk_count > 1

    def test_get_document(self):
        idx = KnowledgeIndexer()
        doc = idx.index("test content", "test.txt")
        retrieved = idx.get_document(doc.id)
        assert retrieved is not None

    def test_get_nonexistent_document(self):
        idx = KnowledgeIndexer()
        assert idx.get_document("nonexistent") is None

    def test_get_chunks(self):
        idx = KnowledgeIndexer()
        doc = idx.index("a\n\nb\n\nc\n\nd\n\ne\n\nf\n\ng", "test.md")
        chunks = idx.get_chunks(doc.id)
        assert len(chunks) > 0

    def test_list_documents(self):
        idx = KnowledgeIndexer()
        idx.index("doc1", "a.txt")
        idx.index("doc2", "b.py")
        docs = idx.list_documents()
        assert len(docs) >= 2

    def test_list_by_type(self):
        idx = KnowledgeIndexer()
        idx.index("a", "a.txt")
        idx.index("b", "b.py")
        idx.index("c", "c.md")
        docs = idx.list_documents(doc_type="markdown")
        assert len(docs) == 1

    def test_delete_document(self):
        idx = KnowledgeIndexer()
        doc = idx.index("test", "test.txt")
        assert idx.delete_document(doc.id) is True
        assert idx.get_document(doc.id) is None

    def test_delete_nonexistent(self):
        idx = KnowledgeIndexer()
        assert idx.delete_document("nonexistent") is False

    def test_search_finds_content(self):
        idx = KnowledgeIndexer()
        idx.index("artificial intelligence and machine learning", "ai.md")
        results = idx.search("artificial intelligence")
        assert len(results) >= 1

    def test_search_no_match(self):
        idx = KnowledgeIndexer()
        idx.index("python code", "test.py")
        results = idx.search("cooking recipes")
        assert len(results) == 0

    def test_stats(self):
        idx = KnowledgeIndexer()
        idx.index("a", "a.txt")
        idx.index("b", "b.md")
        stats = idx.get_stats()
        assert stats["total_documents"] == 2

    def test_clear(self):
        idx = KnowledgeIndexer()
        idx.index("test", "test.txt")
        idx.clear()
        assert idx.get_stats()["total_documents"] == 0


class TestKnowledgeRetriever:
    def test_search(self):
        idx = KnowledgeIndexer()
        idx.index("Python async best practices", "python.md")
        retriever = KnowledgeRetriever(idx)
        results = retriever.search("async")
        assert len(results) >= 1

    def test_search_filter_by_type(self):
        idx = KnowledgeIndexer()
        idx.index("Python code", "test.py")
        idx.index("Markdown notes", "notes.md")
        retriever = KnowledgeRetriever(idx)
        results = retriever.search("notes", doc_type="markdown")
        assert len(results) >= 1

    def test_get_context_for_task(self):
        idx = KnowledgeIndexer()
        idx.index("FastAPI is a modern web framework for Python", "fastapi.md")
        retriever = KnowledgeRetriever(idx)
        ctx = retriever.get_context_for_task("build web API")
        assert "FastAPI" in ctx or "web" in ctx.lower()

    def test_get_context_empty(self):
        idx = KnowledgeIndexer()
        retriever = KnowledgeRetriever(idx)
        ctx = retriever.get_context_for_task("nonexistent")
        assert ctx == ""


class TestKnowledgeAPI:
    async def test_upload_text_file(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/knowledge/upload", files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_web_content(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/v1/knowledge/web", json={"content": "test content", "filename": "test.txt"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_search(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post("/api/v1/knowledge/web", json={"content": "machine learning algorithms"})
            resp = await c.post("/api/v1/knowledge/search", json={"query": "machine learning"})
        data = resp.json()
        assert data["success"] is True

    async def test_list_documents(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/knowledge/documents")
        data = resp.json()
        assert data["success"] is True

    async def test_get_document_by_id(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            create = await c.post("/api/v1/knowledge/web", json={"content": "findme"})
            doc_id = create.json()["document"]["id"]
            resp = await c.get(f"/api/v1/knowledge/documents/{doc_id}")
        assert resp.json()["success"] is True

    async def test_get_nonexistent_document(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/knowledge/documents/nonexistent")
        assert resp.json()["success"] is False

    async def test_delete_document(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            create = await c.post("/api/v1/knowledge/web", json={"content": "tobedeleted"})
            doc_id = create.json()["document"]["id"]
            resp = await c.delete(f"/api/v1/knowledge/documents/{doc_id}")
        assert resp.json()["success"] is True

    async def test_stats(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/knowledge/stats")
        data = resp.json()
        assert data["success"] is True
