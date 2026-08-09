"""
Memory 模块测试
测试 Scanner、Parser、Index 和 Service 的核心功能。
"""

import pytest

from app.memory.index import MemoryIndex
from app.memory.parser import MarkdownParser
from app.memory.scanner import VaultScanner

# === 测试数据 ===

SAMPLE_MD_WITH_FRONTMATTER = """---
title: AI漫剧创作指南
tags:
  - AI
  - 创作
  - 漫剧
---

# AI漫剧创作指南

这是关于AI漫剧的完整指南。

## 基础概念

AI漫剧是利用人工智能技术创作的漫画故事。

## 工具推荐

推荐使用 [[Midjourney]] 和 [[Stable Diffusion]]。

#AI #创作技巧
"""

SAMPLE_MD_SIMPLE = """# Docker优化笔记

## 安装步骤

1. 下载Docker Desktop
2. 配置镜像源

## 常见问题

参考 [[Docker排错手册]]。

#技术笔记 #Docker
"""


@pytest.fixture
def temp_vault(tmp_path):
    """创建临时 Obsidian 知识库"""
    vault = tmp_path / "vault"
    vault.mkdir()

    # 文件1：带 frontmatter
    file1 = vault / "AI漫剧创作指南.md"
    file1.write_text(SAMPLE_MD_WITH_FRONTMATTER, encoding="utf-8")

    # 文件2：简单格式
    file2 = vault / "Docker优化笔记.md"
    file2.write_text(SAMPLE_MD_SIMPLE, encoding="utf-8")

    # 子目录文件
    sub = vault / "03-技术笔记"
    sub.mkdir()
    file3 = sub / "Python技巧.md"
    file3.write_text("# Python技巧\n\n一些Python实用技巧。\n\n#Python #编程", encoding="utf-8")

    # 应该被忽略的目录
    obsidian_dir = vault / ".obsidian"
    obsidian_dir.mkdir()
    (obsidian_dir / "config.json").write_text("{}", encoding="utf-8")

    return vault


# === Scanner 测试 ===

class TestVaultScanner:

    def test_scan_finds_markdown_files(self, temp_vault):
        scanner = VaultScanner(str(temp_vault))
        files = scanner.scan()
        assert len(files) == 3

    def test_scan_ignores_obsidian_dir(self, temp_vault):
        scanner = VaultScanner(str(temp_vault))
        files = scanner.scan()
        paths = [f.relative_path for f in files]
        assert not any(".obsidian" in p for p in paths)

    def test_scan_folder(self, temp_vault):
        scanner = VaultScanner(str(temp_vault))
        files = scanner.scan_folder("03-技术笔记")
        assert len(files) == 1
        assert files[0].name == "Python技巧.md"

    def test_incremental_scan(self, temp_vault):
        scanner = VaultScanner(str(temp_vault))
        # 首次全量扫描
        all_files = scanner.scan(incremental=False)
        assert len(all_files) == 3
        # 增量扫描 (无变化)
        changed = scanner.scan(incremental=True)
        assert len(changed) == 0

    def test_file_hash(self, temp_vault):
        scanner = VaultScanner(str(temp_vault))
        files = scanner.scan()
        for f in files:
            assert f.content_hash != ""
            assert len(f.content_hash) == 32  # MD5 hex


# === Parser 测试 ===

class TestMarkdownParser:

    def test_parse_frontmatter(self):
        parser = MarkdownParser()
        doc = parser.parse_content(SAMPLE_MD_WITH_FRONTMATTER)
        assert doc.frontmatter.get("title") == "AI漫剧创作指南"
        assert "AI" in doc.frontmatter.get("tags", [])

    def test_parse_headings(self):
        parser = MarkdownParser()
        doc = parser.parse_content(SAMPLE_MD_WITH_FRONTMATTER)
        assert len(doc.headings) >= 2
        assert doc.headings[0]["level"] == 1

    def test_parse_tags(self):
        parser = MarkdownParser()
        doc = parser.parse_content(SAMPLE_MD_WITH_FRONTMATTER)
        assert "AI" in doc.tags
        assert "创作" in doc.tags

    def test_parse_wikilinks(self):
        parser = MarkdownParser()
        doc = parser.parse_content(SAMPLE_MD_WITH_FRONTMATTER)
        assert "Midjourney" in doc.wikilinks
        assert "Stable Diffusion" in doc.wikilinks

    def test_parse_keywords(self):
        parser = MarkdownParser()
        doc = parser.parse_content(SAMPLE_MD_WITH_FRONTMATTER)
        assert len(doc.keywords) > 0

    def test_parse_title_from_heading(self):
        parser = MarkdownParser()
        doc = parser.parse_content(SAMPLE_MD_SIMPLE)
        assert doc.title == "Docker优化笔记"

    def test_parse_summary(self):
        parser = MarkdownParser()
        doc = parser.parse_content(SAMPLE_MD_WITH_FRONTMATTER)
        assert len(doc.summary) > 0
        assert "AI漫剧" in doc.summary


# === Index 测试 ===

class TestMemoryIndex:

    def test_upsert_and_search(self, temp_vault):
        index = MemoryIndex(str(temp_vault / "index.db"))
        scanner = VaultScanner(str(temp_vault))
        parser = MarkdownParser()

        files = scanner.scan()
        for f in files:
            doc = parser.parse_file(f.path)
            index.upsert_file(f, doc)

        # 搜索 "AI漫剧"
        results = index.search("AI漫剧")
        assert len(results) > 0
        assert results[0]["title"] == "AI漫剧创作指南"

    def test_search_weights(self, temp_vault):
        index = MemoryIndex(str(temp_vault / "index.db"))
        scanner = VaultScanner(str(temp_vault))
        parser = MarkdownParser()

        files = scanner.scan()
        for f in files:
            doc = parser.parse_file(f.path)
            index.upsert_file(f, doc)

        # 文件名匹配权重最高
        results = index.search("Docker")
        assert len(results) > 0
        # "Docker优化笔记" 文件名匹配，应排第一
        assert results[0]["title"] == "Docker优化笔记"

    def test_stats(self, temp_vault):
        index = MemoryIndex(str(temp_vault / "index.db"))
        scanner = VaultScanner(str(temp_vault))
        parser = MarkdownParser()

        files = scanner.scan()
        for f in files:
            doc = parser.parse_file(f.path)
            index.upsert_file(f, doc)

        stats = index.get_stats()
        assert stats["total_indexed"] == 3