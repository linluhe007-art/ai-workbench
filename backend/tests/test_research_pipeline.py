"""Phase Beta-Search tests - Research Pipeline Integration"""
import pytest
from app.agents.research_agent import ResearchAgent
from app.agents.writing_agent import WritingAgent
from app.search.search_engine import MockSearchProvider, SearchEngine
from app.research.extractor import InformationExtractor
from app.research.citation import CitationManager


class TestResearchPipeline:
    """Test the full research -> extract -> write -> cite pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        # Step 1: Search
        engine = SearchEngine(provider=MockSearchProvider())
        search_resp = await engine.search("AI market trends 2026", max_results=5)
        assert len(search_resp.results) >= 1

        # Step 2: Extract
        extractor = InformationExtractor()
        docs = []
        for sr in search_resp.results:
            doc = extractor.extract(sr.snippet, sr.url, "html")
            docs.append(doc)
        assert len(docs) == len(search_resp.results)

        # Step 3: Research agent
        research_agent = ResearchAgent()
        research_resp = await research_agent.execute_task({
            "task": "AI market trends",
            "query": "AI market trends 2026",
            "max_sources": 5,
        })
        assert research_resp.success
        result = research_resp.data["research_result"]
        assert result["source_count"] >= 1

        # Step 4: Writing agent
        writer = WritingAgent()
        write_resp = await writer.execute_task({
            "task": "AI market trends 2026",
            "output_type": "report",
            "research_result": result,
        })
        assert write_resp.success
        assert write_resp.data["content"] != ""
        assert write_resp.data["source_count"] == result["source_count"]

        # Step 5: Citations
        cm = CitationManager()
        for src in result["sources"]:
            from app.research.citation import Citation
            c = Citation(url=src["url"], title=src["title"])
            cm.record("pipeline-test", c)
        assert cm.get_citation_count("pipeline-test") == result["source_count"]

    @pytest.mark.asyncio
    async def test_pipeline_with_different_output_types(self):
        types = ["report", "article", "analysis"]
        writer = WritingAgent()
        base_result = {"sources": [{"title": "S", "url": "https://s.com"}], "source_count": 1}

        for output_type in types:
            resp = await writer.execute_task({
                "task": "Test",
                "output_type": output_type,
                "research_result": base_result,
            })
            assert resp.success
            assert resp.data["output_type"] == output_type

    @pytest.mark.asyncio
    async def test_pipeline_empty_sources(self):
        writer = WritingAgent()
        resp = await writer.execute_task({
            "task": "Something with no sources",
            "output_type": "report",
            "research_result": {"sources": [], "source_count": 0},
        })
        assert resp.success
        assert "0 sources" in resp.data["content"] or resp.data["source_count"] == 0

    @pytest.mark.asyncio
    async def test_pipeline_artifact_structure(self):
        writer = WritingAgent()
        sources = [
            {"title": f"S{i}", "url": f"https://s{i}.com", "snippet": f"Summary {i}"}
            for i in range(3)
        ]
        resp = await writer.execute_task({
            "task": "Topic",
            "output_type": "report",
            "research_result": {"sources": sources, "source_count": 3},
        })
        artifact = resp.data
        assert "content" in artifact
        assert "citations" in artifact
        assert "output_type" in artifact
        assert artifact["source_count"] == 3

    @pytest.mark.asyncio
    async def test_pipeline_citation_accuracy(self):
        cm = CitationManager()
        from app.research.citation import Citation

        for i in range(5):
            cm.record("acc-test", Citation(url=f"https://ref{i}.com", title=f"Ref {i}"))

        assert cm.get_citation_count("acc-test") == 5
        cites = cm.get_citations("acc-test")
        urls = [c["url"] for c in cites]
        for i in range(5):
            assert f"https://ref{i}.com" in urls
