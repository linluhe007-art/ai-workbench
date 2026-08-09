"""
Markdown 内容解析器
解析 Markdown 文件的结构化内容：标题层级、正文、标签、内部链接、元数据。
"""

import re
from dataclasses import dataclass
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

# 正则模式
TAG_PATTERN = re.compile(r"(?:^|\s)#([a-zA-Z\u4e00-\u9fff][\w\u4e00-\u9fff/]*)")
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")  # [[target]] 或 [[target|alias]]


@dataclass
class ParsedSection:
    """解析后的文档段落"""
    heading: str
    level: int
    content: str


@dataclass
class ParsedDocument:
    """解析后的完整文档"""
    title: str
    tags: list[str]
    frontmatter: dict
    headings: list[dict]            # [{level, text}]
    sections: list[ParsedSection]
    wikilinks: list[str]            # Obsidian 内部链接 [[...]]
    keywords: list[str]             # 提取的关键词
    full_text: str
    summary: str


class MarkdownParser:
    """
    Markdown 内容解析器
    支持：YAML frontmatter、标题层级、Obsidian 标签、内部链接、关键词提取。
    """

    def parse_file(self, file_path: str) -> ParsedDocument:
        """解析文件"""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            return self.parse_content(content, file_path)
        except Exception as e:  # noqa: BLE001 — parse failure returns empty doc
            logger.error("Failed to parse file", path=file_path, error=str(e))
            return self._empty_doc()

    def parse_content(self, content: str, source: str = "") -> ParsedDocument:
        """解析 Markdown 文本内容"""
        if not content.strip():
            return self._empty_doc()

        frontmatter, body = self._extract_frontmatter(content)
        tags = self._extract_tags(content, frontmatter)
        headings = self._extract_headings(body)
        title = self._extract_title(headings, frontmatter, source)
        sections = self._parse_sections(body)
        wikilinks = self._extract_wikilinks(content)
        keywords = self._extract_keywords(title, headings, tags)
        full_text = self._to_plain_text(body)
        summary = self._generate_summary(full_text, headings)

        return ParsedDocument(
            title=title,
            tags=tags,
            frontmatter=frontmatter,
            headings=headings,
            sections=sections,
            wikilinks=wikilinks,
            keywords=keywords,
            full_text=full_text,
            summary=summary,
        )

    def _extract_frontmatter(self, content: str) -> tuple[dict, str]:
        """提取 YAML frontmatter"""
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}, content

        body = content[match.end():]
        raw = match.group(1)

        fm: dict = {}
        current_key = None
        current_list: list | None = None

        for line in raw.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line and not line.startswith("-"):
                if current_key and current_list is not None:
                    fm[current_key] = current_list
                key, _, val = line.partition(":")
                current_key = key.strip()
                val = val.strip()
                if val:
                    fm[current_key] = val.strip("\"'")
                    current_list = None
                else:
                    current_list = []
            elif line.startswith("-") and current_key and current_list is not None:
                current_list.append(line.lstrip("- ").strip())

        if current_key and current_list is not None:
            fm[current_key] = current_list

        return fm, body

    def _extract_tags(self, content: str, frontmatter: dict) -> list[str]:
        """提取所有标签 (frontmatter + 行内)"""
        tags: set[str] = set()

        fm_tags = frontmatter.get("tags", [])
        if isinstance(fm_tags, list):
            tags.update(fm_tags)
        elif isinstance(fm_tags, str):
            tags.update(t.strip() for t in fm_tags.split(","))

        for match in TAG_PATTERN.finditer(content):
            tag = match.group(1)
            if not tag.startswith(("include", "define", "pragma", "ifndef")):
                tags.add(tag)

        return sorted(tags)

    def _extract_headings(self, body: str) -> list[dict]:
        """提取所有标题"""
        return [
            {"level": len(m.group(1)), "text": m.group(2).strip()}
            for m in HEADING_PATTERN.finditer(body)
        ]

    def _extract_title(self, headings: list[dict], frontmatter: dict, source: str) -> str:
        """提取文档标题"""
        if "title" in frontmatter:
            return frontmatter["title"]
        for h in headings:
            if h["level"] == 1:
                return h["text"]
        if source:
            return Path(source).stem
        return "Untitled"

    def _parse_sections(self, body: str) -> list[ParsedSection]:
        """按标题拆分结构化段落"""
        sections: list[ParsedSection] = []
        lines = body.split("\n")
        current: ParsedSection | None = None
        content_lines: list[str] = []

        for line in lines:
            heading_match = HEADING_PATTERN.match(line)
            if heading_match:
                if current is not None:
                    current.content = "\n".join(content_lines).strip()
                    sections.append(current)
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                current = ParsedSection(heading=text, level=level, content="")
                content_lines = []
            else:
                content_lines.append(line)

        if current is not None:
            current.content = "\n".join(content_lines).strip()
            sections.append(current)

        return sections

    def _extract_wikilinks(self, content: str) -> list[str]:
        """提取 Obsidian 内部链接 [[...]]"""
        return list(set(WIKILINK_PATTERN.findall(content)))

    def _extract_keywords(self, title: str, headings: list[dict], tags: list[str]) -> list[str]:
        """提取关键词：标题词 + 标签"""
        keywords: set[str] = set(tags)

        # 从标题提取
        title_words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", title)
        keywords.update(w for w in title_words if len(w) >= 2)

        # 从 H2/H3 标题提取
        for h in headings:
            if h["level"] <= 3:
                words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", h["text"])
                keywords.update(w for w in words if len(w) >= 2)

        return sorted(keywords)

    def _to_plain_text(self, body: str) -> str:
        """去除 Markdown 格式"""
        text = re.sub(r"```[\s\S]*?```", "[代码块]", body)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"!\[.*?\]\(.*?\)", "[图片]", text)
        text = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)  # wikilink → 纯文本
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"\*([^*]+)\*", r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _generate_summary(self, full_text: str, headings: list[dict]) -> str:
        """生成摘要：取前 500 字，优先保留段落完整"""
        if len(full_text) <= 500:
            return full_text
        # 找到 500 字附近的段落边界
        cut = full_text[:500]
        last_para = cut.rfind("\n\n")
        if last_para > 200:
            return cut[:last_para].strip()
        return cut.strip() + "..."

    def _empty_doc(self) -> ParsedDocument:
        return ParsedDocument(
            title="", tags=[], frontmatter={},
            headings=[], sections=[], wikilinks=[],
            keywords=[], full_text="", summary=""
        )