"""
Knowledge Parser - Phase 5.4
Document content extraction for PDF, Markdown, TXT, code files, and web content.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentType(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    TXT = "txt"
    CODE = "code"
    WEB = "web"
    UNKNOWN = "unknown"


@dataclass
class ParsedKnowledge:
    title: str = ""
    content: str = ""
    doc_type: DocumentType = DocumentType.UNKNOWN
    metadata: dict = field(default_factory=dict)
    chunks: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    summary: str = ""


class KnowledgeParser:
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
        ".cpp", ".c", ".h", ".cs", ".rb", ".php", ".swift", ".kt",
        ".sh", ".yaml", ".yml", ".toml", ".json", ".xml", ".sql",
        ".r", ".scala", ".dart",
    }

    def parse(self, content: str, filename: str = "", source_url: str = "") -> ParsedKnowledge:
        doc_type = self._detect_type(filename, content)
        title = self._extract_title(filename, content, doc_type)
        cleaned = self._clean_content(content, doc_type)
        chunks = self._chunk_content(cleaned)
        tags = self._extract_tags(cleaned, doc_type)
        summary = self._generate_summary(cleaned, doc_type)
        return ParsedKnowledge(
            title=title, content=cleaned, doc_type=doc_type,
            metadata={"filename": filename, "source_url": source_url, "length": len(content)},
            chunks=chunks, tags=tags, summary=summary,
        )

    def parse_file(self, file_path: str) -> ParsedKnowledge:
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return self.parse(content, path.name)
        except Exception as e:
            logger.error("Failed to parse file", path=file_path, error=str(e))
            return ParsedKnowledge(title=path.name, doc_type=DocumentType.UNKNOWN)

    def _detect_type(self, filename: str, content: str) -> DocumentType:
        ext = Path(filename).suffix.lower() if filename else ""
        if ext == ".pdf":
            return DocumentType.PDF
        if ext in (".md", ".markdown"):
            return DocumentType.MARKDOWN
        if ext in self.CODE_EXTENSIONS:
            return DocumentType.CODE
        if ext in (".txt", ".text", ""):
            return DocumentType.TXT
        return DocumentType.TXT

    def _extract_title(self, filename: str, content: str, doc_type: DocumentType) -> str:
        if filename:
            name = re.sub(r"[-_]+", " ", Path(filename).stem).strip()
            if name:
                return name
        if doc_type == DocumentType.MARKDOWN:
            m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if m:
                return m.group(1).strip()
        for line in content.splitlines()[:5]:
            s = line.strip()
            if s and not s.startswith("#"):
                return s[:80]
        return "Untitled"

    def _clean_content(self, content: str, doc_type: DocumentType) -> str:
        if doc_type == DocumentType.WEB:
            return self._clean_html(content)
        return content.strip()

    def _clean_html(self, content: str) -> str:
        c = content
        c = re.sub(r"<script[^>]*>.*?</script>", "", c, flags=re.DOTALL | re.IGNORECASE)
        c = re.sub(r"<style[^>]*>.*?</style>", "", c, flags=re.DOTALL | re.IGNORECASE)
        BLOCK_TAGS = ["p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"]
        for tag in BLOCK_TAGS:
            c = re.sub(r"</?" + tag + r"[^>]*>", "\n", c, flags=re.IGNORECASE)
        c = re.sub(r"<[^>]+>", " ", c)
        c = c.replace("&nbsp;", " ").replace("&amp;", "&")
        c = c.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", chr(34))
        c = re.sub(r"\n{3,}", "\n\n", c)
        c = re.sub(r"[ \t]{2,}", " ", c)
        return c.strip()

    def _chunk_content(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        if not content.strip():
            return []
        paragraphs = re.split(r"\n\s*\n", content)
        chunks: list[str] = []
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) + 2 <= chunk_size:
                current = (current + "\n\n" + para).strip() if current else para
            else:
                if current:
                    chunks.append(current)
                if len(para) > chunk_size:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    sub = ""
                    for s in sentences:
                        if len(sub) + len(s) + 1 <= chunk_size:
                            sub = (sub + " " + s).strip() if sub else s
                        else:
                            if sub:
                                chunks.append(sub)
                            sub = s
                    if sub:
                        chunks.append(sub)
                else:
                    chunks.append(para)
                current = ""
        if current:
            chunks.append(current)
        return chunks

    def _extract_tags(self, content: str, doc_type: DocumentType) -> list[str]:
        if doc_type == DocumentType.CODE:
            return ["code"]
        tags: set[str] = set()
        KEYWORD_MAP = {
            "python": ["python", "django", "flask", "fastapi", "pandas"],
            "javascript": ["javascript", "typescript", "react", "node", "vue"],
            "ai": ["machine learning", "deep learning", "nlp", "neural network", "ai"],
            "database": ["database", "sql", "postgres", "mysql", "mongodb"],
            "docker": ["docker", "container", "kubernetes", "k8s"],
            "api": ["api", "rest", "graphql", "grpc"],
            "security": ["security", "auth", "jwt", "oauth", "encrypt"],
            "testing": ["test", "testing", "pytest", "jest", "coverage"],
        }
        cl = content.lower()
        for tag, keywords in KEYWORD_MAP.items():
            for kw in keywords:
                if kw in cl:
                    tags.add(tag)
                    break
        return sorted(tags)

    def _generate_summary(self, content: str, doc_type: DocumentType, max_len: int = 300) -> str:
        if not content.strip():
            return ""
        lines = content.strip().splitlines()
        parts = []
        for line in lines:
            text = line.strip()
            if text and len(text) > 30 and not text.startswith("#"):
                parts.append(text[:200])
                break
        for line in lines[1:]:
            text = line.strip()
            if text and len(text) > 30 and not text.startswith("#") and text not in parts:
                snippet = text[:200]
                if len(" ".join(parts)) + len(snippet) < max_len:
                    parts.append(snippet)
                break
        return " ".join(parts)[:max_len]
