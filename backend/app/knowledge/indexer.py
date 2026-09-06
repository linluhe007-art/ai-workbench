"""
Knowledge Indexer - Phase 5.4
Indexes parsed knowledge documents with chunk-level and document-level storage.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.knowledge.parser import KnowledgeParser, ParsedKnowledge, DocumentType
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KnowledgeDocument:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    doc_type: str = "unknown"
    content: str = ""
    filename: str = ""
    source_url: str = ""
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    metadata: dict = field(default_factory=dict)
    chunk_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "doc_type": self.doc_type,
            "filename": self.filename, "source_url": self.source_url,
            "tags": self.tags, "summary": self.summary,
            "metadata": self.metadata, "chunk_count": self.chunk_count,
            "created_at": self.created_at,
        }


@dataclass
class KnowledgeChunk:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    chunk_index: int = 0
    content: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "document_id": self.document_id,
            "chunk_index": self.chunk_index, "content": self.content,
            "tags": self.tags, "created_at": self.created_at,
        }


class KnowledgeIndexer:
    def __init__(self):
        self._parser = KnowledgeParser()
        self._documents: dict[str, KnowledgeDocument] = {}
        self._chunks: dict[str, KnowledgeChunk] = {}
        self._doc_chunks: dict[str, list[str]] = {}

    def index(self, content: str, filename: str = "", source_url: str = "") -> KnowledgeDocument:
        parsed = self._parser.parse(content, filename, source_url)
        doc = KnowledgeDocument(
            title=parsed.title, doc_type=parsed.doc_type.value,
            content=parsed.content, filename=parsed.metadata.get("filename", ""),
            source_url=parsed.metadata.get("source_url", ""),
            tags=parsed.tags, summary=parsed.summary,
            metadata=parsed.metadata, chunk_count=len(parsed.chunks),
        )
        self._documents[doc.id] = doc
        self._doc_chunks[doc.id] = []
        for i, chunk_text in enumerate(parsed.chunks):
            chunk = KnowledgeChunk(document_id=doc.id, chunk_index=i, content=chunk_text, tags=parsed.tags)
            self._chunks[chunk.id] = chunk
            self._doc_chunks[doc.id].append(chunk.id)
        logger.info("Document indexed", title=doc.title, chunks=doc.chunk_count, doc_type=parsed.doc_type.value)
        return doc

    def get_document(self, doc_id: str):
        return self._documents.get(doc_id)

    def get_chunks(self, doc_id: str) -> list[KnowledgeChunk]:
        chunk_ids = self._doc_chunks.get(doc_id, [])
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    def list_documents(self, limit: int = 50, doc_type: str | None = None) -> list[dict]:
        docs = list(self._documents.values())
        if doc_type:
            docs = [d for d in docs if d.doc_type == doc_type]
        docs.sort(key=lambda d: d.created_at, reverse=True)
        return [d.to_dict() for d in docs[:limit]]

    def delete_document(self, doc_id: str) -> bool:
        doc = self._documents.pop(doc_id, None)
        if not doc:
            return False
        for cid in self._doc_chunks.pop(doc_id, []):
            self._chunks.pop(cid, None)
        return True

    def search(self, query: str, limit: int = 20) -> list[dict]:
        query_lower = query.lower()
        results = []
        for chunk in self._chunks.values():
            score = self._score_chunk(chunk, query_lower)
            if score > 0:
                doc = self._documents.get(chunk.document_id)
                results.append({
                    "chunk_id": chunk.id, "document_id": chunk.document_id,
                    "content": chunk.content[:500], "score": score,
                    "title": doc.title if doc else "",
                    "doc_type": doc.doc_type if doc else "unknown",
                })
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    def _score_chunk(self, chunk: KnowledgeChunk, query_lower: str) -> float:
        score = 0.0
        content_lower = chunk.content.lower()
        if query_lower in content_lower:
            score += 2.0
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        overlap = query_words & content_words
        if overlap:
            score += len(overlap) / len(query_words)
        for tag in chunk.tags:
            if query_lower in tag.lower():
                score += 0.5
        return round(score, 4)

    def get_stats(self) -> dict:
        type_counts = {}
        for doc in self._documents.values():
            type_counts[doc.doc_type] = type_counts.get(doc.doc_type, 0) + 1
        return {"total_documents": len(self._documents), "total_chunks": len(self._chunks), "by_type": type_counts}

    def clear(self) -> None:
        self._documents.clear()
        self._chunks.clear()
        self._doc_chunks.clear()
