"""
Knowledge API - Phase 5.4
Document upload, search, listing for personal knowledge base.
"""

from fastapi import APIRouter, UploadFile, File, Form, Query
from pydantic import BaseModel

from app.knowledge.indexer import KnowledgeIndexer
from app.knowledge.parser import KnowledgeParser, DocumentType
from app.knowledge.retriever import KnowledgeRetriever
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_indexer: KnowledgeIndexer | None = None
_retriever: KnowledgeRetriever | None = None


def _get_indexer() -> KnowledgeIndexer:
    global _indexer
    if _indexer is None:
        _indexer = KnowledgeIndexer()
    return _indexer


def _get_retriever() -> KnowledgeRetriever:
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever(_get_indexer())
    return _retriever


class WebContentRequest(BaseModel):
    content: str
    source_url: str = ""
    filename: str = ""


class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    doc_type: str | None = None


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a document file."""
    try:
        content = (await file.read()).decode("utf-8", errors="replace")
        filename = file.filename or "uploaded"
        indexer = _get_indexer()
        doc = indexer.index(content, filename=filename)
        return {"success": True, "document": doc.to_dict()}
    except Exception as e:
        logger.error("Upload failed", error=str(e))
        return {"success": False, "error": str(e)}


@router.post("/web")
async def index_web_content(req: WebContentRequest):
    """Index web content or text directly."""
    try:
        indexer = _get_indexer()
        doc = indexer.index(req.content, filename=req.filename, source_url=req.source_url)
        return {"success": True, "document": doc.to_dict()}
    except Exception as e:
        logger.error("Web index failed", error=str(e))
        return {"success": False, "error": str(e)}


@router.post("/search")
async def search_knowledge(req: SearchRequest):
    """Search indexed knowledge chunks."""
    retriever = _get_retriever()
    results = retriever.search(req.query, limit=req.limit, doc_type=req.doc_type)
    return {"success": True, "query": req.query, "total": len(results), "results": results}


@router.get("/documents")
async def list_documents(
    doc_type: str | None = Query(default=None),
    limit: int = Query(default=50),
):
    """List indexed documents."""
    indexer = _get_indexer()
    docs = indexer.list_documents(limit=limit, doc_type=doc_type)
    return {"success": True, "total": len(docs), "documents": docs}


@router.get("/documents/{doc_id}")
async def get_document(doc_id: str):
    """Get a document by ID with its chunks."""
    indexer = _get_indexer()
    doc = indexer.get_document(doc_id)
    if not doc:
        return {"success": False, "error": "Document not found"}
    chunks = indexer.get_chunks(doc_id)
    return {
        "success": True,
        "document": doc.to_dict(),
        "chunks": [c.to_dict() for c in chunks],
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its chunks."""
    indexer = _get_indexer()
    deleted = indexer.delete_document(doc_id)
    if not deleted:
        return {"success": False, "error": "Document not found"}
    return {"success": True, "message": "Document deleted"}


@router.get("/stats")
async def get_stats():
    """Get knowledge base statistics."""
    indexer = _get_indexer()
    return {"success": True, "data": indexer.get_stats()}


@router.get("/context")
async def get_context(q: str = Query(..., description="Task description"), limit: int = 5):
    """Get relevant knowledge context for a task (Agent integration)."""
    retriever = _get_retriever()
    context_text = retriever.get_context_for_task(q, limit=limit)
    return {"success": True, "query": q, "context": context_text}
