"""
Knowledge Retriever - Phase 5.4
Semantic search over indexed knowledge chunks.
"""

from app.knowledge.indexer import KnowledgeIndexer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeRetriever:
    def __init__(self, indexer: KnowledgeIndexer | None = None):
        self._indexer = indexer or KnowledgeIndexer()

    def search(self, query: str, limit: int = 10, doc_type: str | None = None) -> list[dict]:
        results = self._indexer.search(query, limit=limit * 2)
        if doc_type:
            results = [r for r in results if r.get("doc_type") == doc_type]
        return results[:limit]

    def get_context_for_task(self, task: str, limit: int = 5) -> str:
        results = self.search(task, limit=limit)
        if not results:
            return ""
        parts = ["## Relevant Knowledge\n"]
        for r in results:
            parts.append(f"- [{r['title']}] {r['content'][:200]}")
        return "\n".join(parts)
