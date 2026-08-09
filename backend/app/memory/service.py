"""
Memory 服务层
对外提供统一的知识库查询接口。
支持按 Agent 类型返回差异化上下文。
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings
from app.memory.index import MemoryIndex
from app.memory.parser import MarkdownParser
from app.memory.scanner import VaultScanner
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemoryContext:
    """
    结构化记忆上下文
    根据 agent_type 返回差异化内容。
    """
    documents: list[dict]
    tags: list[str]
    related_links: list[str]
    summary: str
    style_info: str = ""        # 写作风格信息 (ContentAgent 用)
    examples: list[str] = field(default_factory=list)  # 示例内容
    references: list[dict] = field(default_factory=list)  # 参考来源 (ResearchAgent 用)

    def to_prompt(self) -> str:
        """转为可注入 Prompt 的文本"""
        parts = ["# 知识库上下文\n"]

        if self.documents:
            parts.append("## 相关文档")
            for doc in self.documents[:5]:
                parts.append(f"- **{doc['title']}** ({doc['path']})")
                if doc.get("summary"):
                    parts.append(f"  摘要: {doc['summary'][:200]}")

        if self.tags:
            parts.append(f"\n## 相关标签\n{', '.join(self.tags[:10])}")

        if self.related_links:
            parts.append(f"\n## 相关链接\n{', '.join(self.related_links[:10])}")

        if self.style_info:
            parts.append(f"\n## 写作风格参考\n{self.style_info}")

        if self.examples:
            parts.append("\n## 参考示例")
            for ex in self.examples[:3]:
                parts.append(f"- {ex[:150]}")

        if self.references:
            parts.append("\n## 参考来源")
            for ref in self.references[:5]:
                parts.append(f"- {ref.get('title', '')} ({ref.get('path', '')})")

        if self.summary:
            parts.append(f"\n## 详细内容\n{self.summary}")

        return "\n".join(parts)


class MemoryService:
    """
    Memory 服务 — 个人知识库记忆层
    支持按 Agent 类型返回差异化上下文：
    - ContentAgent: summary + style + examples
    - ResearchAgent: documents + references + links
    - KnowledgeAgent: tags + graph relations
    """

    def __init__(self, vault_path: str | None = None):
        settings = get_settings()
        self.vault_path = vault_path or settings.obsidian_vault_path
        self.scanner = VaultScanner(self.vault_path)
        self.parser = MarkdownParser()
        self.index = MemoryIndex()
        logger.info("MemoryService initialized", vault=self.vault_path)

    def refresh(self) -> int:
        files = self.scanner.scan()
        return self.index.bulk_update(files)

    def incremental_refresh(self) -> int:
        changed = self.scanner.scan(incremental=True)
        if not changed:
            return 0
        return self.index.bulk_update(changed)

    def search(self, keyword: str, limit: int = 10) -> list[dict]:
        return self.index.search(keyword, limit=limit)

    def search_by_tag(self, tag: str, limit: int = 10) -> list[dict]:
        return self.index.search_by_tag(tag, limit=limit)

    def get_context(self, task: str, agent_type: str | None = None, max_chars: int = 3000) -> str:
        """向后兼容接口：返回纯文本上下文"""
        ctx = self.get_memory_context(task, agent_type=agent_type, max_chars=max_chars)
        return ctx.to_prompt()

    def get_memory_context(self, task: str, agent_type: str | None = None, max_chars: int = 3000) -> MemoryContext:
        """
        获取结构化记忆上下文
        Args:
            task: 任务描述或关键词
            agent_type: Agent 类型 (content/research/knowledge/None)
            max_chars: 最大字符数
        """
        search_results = self.index.search(task, limit=10)

        # 收集公共字段
        all_tags: set[str] = set()
        all_links: set[str] = set()
        for r in search_results:
            all_tags.update(r.get("tags", []))
            all_links.update(r.get("wikilinks", []))

        documents = [
            {"title": r["title"], "path": r["path"], "summary": r.get("summary", ""), "relevance": r["relevance"]}
            for r in search_results
        ]

        # 生成摘要
        summary_parts, total_len = [], 0
        for r in search_results:
            block = f"### {r['title']}\n来源: {r['path']}\n{r.get('summary', '')}\n\n"
            if total_len + len(block) > max_chars:
                break
            summary_parts.append(block)
            total_len += len(block)

        # 按 Agent 类型差异化
        style_info = ""
        examples: list[str] = []
        references: list[dict] = []

        if agent_type == "content":
            # ContentAgent: 关注写作风格和示例
            style_info = self._extract_style_info(search_results)
            examples = self._extract_examples(search_results)
        elif agent_type == "research":
            # ResearchAgent: 关注参考来源
            references = [
                {"title": r["title"], "path": r["path"], "summary": r.get("summary", "")}
                for r in search_results[:5]
            ]
        elif agent_type == "knowledge":
            # KnowledgeAgent: 关注标签和链接关系 (已在公共字段中)
            pass

        return MemoryContext(
            documents=documents,
            tags=sorted(all_tags),
            related_links=sorted(all_links),
            summary="".join(summary_parts) if summary_parts else "未找到相关知识库内容。",
            style_info=style_info,
            examples=examples,
            references=references,
        )

    def _extract_style_info(self, results: list[dict]) -> str:
        """从搜索结果中提取写作风格信息"""
        style_parts = []
        for r in results[:3]:
            tags = r.get("tags", [])
            if any(t in tags for t in ["写作风格", "模板", "风格"]):
                style_parts.append(f"- {r['title']}: {r.get('summary', '')[:100]}")
        return "\n".join(style_parts) if style_parts else ""

    def _extract_examples(self, results: list[dict]) -> list[str]:
        """从搜索结果中提取示例内容"""
        examples = []
        for r in results[:3]:
            if r.get("summary"):
                examples.append(f"[{r['title']}] {r['summary'][:200]}")
        return examples

    def get_stats(self) -> dict:
        scanner_stats = {
            "vault_path": self.vault_path,
            "vault_exists": Path(self.vault_path).exists(),
        }
        index_stats = self.index.get_stats()
        return {**scanner_stats, **index_stats}