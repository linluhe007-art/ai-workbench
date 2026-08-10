"""
MemoryTool — 知识库搜索工具
调用 MemoryService.search() 查询用户知识库。
可被 Agent 通过 call_llm() + function calling 使用。
"""

from typing import Any

from app.tools.base import BaseTool, ToolResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryTool(BaseTool):
    """
    搜索用户个人知识库
    基于关键词检索 Obsidian Markdown 索引，返回匹配的记忆条目。
    """

    def __init__(self, memory_service: Any = None):
        """
        Args:
            memory_service: MemoryService 实例。不传则延迟初始化。
        """
        self._memory = memory_service

    def _get_memory(self):
        if self._memory is None:
            from app.memory.service import MemoryService
            self._memory = MemoryService()
        return self._memory

    @property
    def name(self) -> str:
        return "memory_search"

    @property
    def description(self) -> str:
        return "搜索用户个人知识库，根据关键词查找相关文档、标签和摘要"

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        执行搜索
        Args:
            query: 搜索关键词 (必填)
            limit: 返回结果数量上限 (默认 5)
        Returns:
            ToolResult(success=True, data={"memories": [...]})
        """
        query = kwargs.get("query", "")
        if not query or not isinstance(query, str) or not query.strip():
            return ToolResult(success=False, error="query 参数不能为空")

        limit = kwargs.get("limit", 5)
        if not isinstance(limit, int) or limit < 1:
            limit = 5

        try:
            memory = self._get_memory()
            results = memory.search(query.strip(), limit=limit)

            memories = []
            for r in results:
                memories.append({
                    "title": r.get("title", ""),
                    "path": r.get("path", ""),
                    "summary": r.get("summary", ""),
                    "tags": r.get("tags", []),
                    "relevance": r.get("relevance", 0),
                })

            return ToolResult(
                success=True,
                data={"memories": memories},
                metadata={"query": query, "limit": limit, "count": len(memories)},
            )
        except Exception as e:  # noqa: BLE001 — tool wraps all errors
            logger.error("MemoryTool execute failed", query=query, error=str(e))
            return ToolResult(success=False, error=str(e))

    def _parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量上限，默认 5",
                },
            },
            "required": ["query"],
        }