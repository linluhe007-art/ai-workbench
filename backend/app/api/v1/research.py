"""Research API - Phase Beta-Search"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.research_agent import ResearchAgent
from app.agents.writing_agent import WritingAgent
from app.search.search_engine import get_search_engine
from app.research.citation import get_citation_manager
from app.research.extractor import get_extractor
from app.llm.events import publish_llm_event
from app.llm.factory import get_llm_provider
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str
    output_type: str = "report"
    max_sources: int = 10


class ResearchTaskState:
    """Simple in-memory task state tracking."""

    def __init__(self):
        self._tasks: dict[str, dict] = {}

    def create(self, task_id: str, query: str, output_type: str) -> dict:
        self._tasks[task_id] = {
            "task_id": task_id,
            "query": query,
            "output_type": output_type,
            "status": "created",
            "sources": [],
            "research_result": None,
            "final_artifact": None,
        }
        return self._tasks[task_id]

    def update(self, task_id: str, **kwargs):
        if task_id in self._tasks:
            self._tasks[task_id].update(kwargs)

    def get(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)


_task_state = ResearchTaskState()


@router.post("")
async def start_research(req: ResearchRequest):
    """Start a new research task."""
    import uuid
    task_id = str(uuid.uuid4())
    state = _task_state.create(task_id, req.query, req.output_type)

    publish_llm_event("research_started", {"query": req.query, "output_type": req.output_type}, task_id=task_id)

    # Execute research pipeline
    llm_provider = get_llm_provider()
    research_agent = ResearchAgent(llm_provider=llm_provider)
    search_engine = get_search_engine()

    # Step 1: Search
    search_response = await search_engine.search(req.query, max_results=req.max_sources)
    sources = [r.to_dict() for r in search_response.results]

    # Step 2: Extract
    extractor = get_extractor()
    documents = []
    for sr in search_response.results:
        doc = extractor.extract(sr.snippet, sr.url, "html")
        documents.append(doc.to_dict())

    # Step 3: Build research result
    research_result_data = {
        "query": req.query,
        "sources": sources,
        "extracted_documents": documents,
        "source_count": len(sources),
    }

    # Step 4: Write
    publish_llm_event("writing_started", {"query": req.query}, task_id=task_id)
    writing_agent = WritingAgent(llm_provider=llm_provider)
    write_response = await writing_agent.execute_task({
        "task": req.query,
        "research_result": research_result_data,
        "output_type": req.output_type,
    })

    # Step 5: Record citations
    citation_mgr = get_citation_manager()
    for src in sources:
        from app.research.citation import Citation
        cit = Citation(url=src["url"], title=src["title"], source_type="web")
        citation_mgr.record(task_id, cit)

    # Build final artifact
    artifact = {
        "type": "markdown",
        "name": f"research_{req.output_type}",
        "content": write_response.data.get("content", ""),
        "metadata": {
            "task_id": task_id,
            "query": req.query,
            "output_type": req.output_type,
            "source_count": len(sources),
            "citations": write_response.data.get("citations", []),
            "agent_chain": ["research_agent", "extractor", "writer_agent"],
        },
    }

    publish_llm_event("writing_completed", {"source_count": len(sources)}, task_id=task_id)

    _task_state.update(task_id,
        status="completed",
        sources=sources,
        research_result=research_result_data,
        final_artifact=artifact,
    )

    publish_llm_event("research_completed", {"source_count": len(sources)}, task_id=task_id)

    return {
        "success": True,
        "task_id": task_id,
        "status": "completed",
        "source_count": len(sources),
    }


@router.get("/{task_id}/sources")
async def get_sources(task_id: str):
    """Get search sources for a research task."""
    state = _task_state.get(task_id)
    if not state:
        return {"success": False, "error": "Task not found"}
    return {"success": True, "task_id": task_id, "sources": state.get("sources", [])}


@router.get("/{task_id}/result")
async def get_result(task_id: str):
    """Get the final research artifact."""
    state = _task_state.get(task_id)
    if not state:
        return {"success": False, "error": "Task not found"}

    citations = get_citation_manager().get_citations(task_id)
    return {
        "success": True,
        "task_id": task_id,
        "artifact": state.get("final_artifact"),
        "citations": citations,
        "status": state.get("status"),
    }
