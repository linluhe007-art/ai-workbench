"""Information Extractor - Phase Beta-Search

Extracts and cleans content from web sources.
Supports HTML, JSON, RSS, and Markdown formats.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Document:
    """Extracted and cleaned document from a source."""
    source: str = ""
    title: str = ""
    content: str = ""
    content_type: str = "text"
    metadata: dict = field(default_factory=dict)
    extracted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "content": self.content,
            "content_type": self.content_type,
            "metadata": self.metadata,
            "extracted_at": self.extracted_at,
        }


class InformationExtractor:
    """Extracts and cleans content from various source formats."""

    def extract(self, raw_content: str, source_url: str = "", content_type: str = "html") -> Document:
        if content_type == "html":
            return self._extract_html(raw_content, source_url)
        elif content_type == "json":
            return self._extract_json(raw_content, source_url)
        elif content_type == "rss":
            return self._extract_rss(raw_content, source_url)
        elif content_type == "markdown":
            return self._extract_markdown(raw_content, source_url)
        else:
            return self._extract_text(raw_content, source_url)

    def _extract_html(self, raw: str, url: str) -> Document:
        cleaned = self._strip_html_tags(raw)
        cleaned = self._clean_text(cleaned)
        title = self._extract_title(cleaned, url)
        return Document(source=url, title=title, content=cleaned, content_type="text")

    def _extract_json(self, raw: str, url: str) -> Document:
        import json
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, dict):
                title = data.get("title", data.get("name", url))
                content = json.dumps(data, ensure_ascii=False, indent=2)
                return Document(source=url, title=str(title), content=content, content_type="json", metadata={"keys": list(data.keys())})
        except (json.JSONDecodeError, TypeError):
            pass
        return self._extract_text(raw, url)

    def _extract_rss(self, raw: str, url: str) -> Document:
        cleaned = self._strip_html_tags(raw)
        cleaned = self._clean_text(cleaned)
        return Document(source=url, title=url, content=cleaned, content_type="text")

    def _extract_markdown(self, raw: str, url: str) -> Document:
        title = self._extract_title(raw, url)
        return Document(source=url, title=title, content=raw, content_type="markdown")

    def _extract_text(self, raw: str, url: str) -> Document:
        cleaned = self._clean_text(raw)
        title = self._extract_title(cleaned, url)
        return Document(source=url, title=title, content=cleaned, content_type="text")

    def _strip_html_tags(self, html: str) -> str:
        clean = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<script[^>]*>.*?</script>', '', clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'&[a-z]+;', ' ', clean)
        clean = re.sub(r'&#[0-9]+;', ' ', clean)
        return clean

    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def _extract_title(self, text: str, fallback: str) -> str:
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) < 200:
                return line
        return fallback or "Untitled"


_extractor: InformationExtractor | None = None


def get_extractor() -> InformationExtractor:
    global _extractor
    if _extractor is None:
        _extractor = InformationExtractor()
    return _extractor
