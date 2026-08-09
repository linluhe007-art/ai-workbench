"""
MemoryIndex 测试
覆盖：FTS5 搜索、权重排序、hash 变化检测、schema migration。
"""


import pytest

from app.memory.index import SCHEMA_VERSION, MemoryIndex
from app.memory.parser import MarkdownParser
from app.memory.scanner import VaultScanner


@pytest.fixture
def index_db(tmp_path):
    """创建临时索引"""
    return str(tmp_path / "test_index.db")


@pytest.fixture
def sample_vault(tmp_path):
    """创建临时知识库"""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "AI漫剧创作指南.md").write_text(
        "---\ntitle: AI漫剧创作指南\ntags:\n  - AI\n  - 创作\n---\n# AI漫剧创作指南\n\n关于AI漫剧的完整指南。\n\n#AI #创作技巧",
        encoding="utf-8"
    )
    (vault / "Docker优化笔记.md").write_text(
        "# Docker优化笔记\n\n## 安装步骤\n\nDocker安装和配置。\n\n#技术笔记 #Docker",
        encoding="utf-8"
    )
    sub = vault / "03-技术笔记"
    sub.mkdir()
    (sub / "Python技巧.md").write_text(
        "# Python技巧\n\nPython实用技巧。\n\n#Python #编程",
        encoding="utf-8"
    )
    return vault


class TestMemoryIndexFTS:

    def test_fts5_search(self, index_db, sample_vault):
        index = MemoryIndex(index_db)
        scanner = VaultScanner(str(sample_vault))
        parser = MarkdownParser()
        for f in scanner.scan():
            index.upsert_file(f, parser.parse_file(f.path))

        results = index.search("AI漫剧")
        assert len(results) > 0
        assert results[0]["title"] == "AI漫剧创作指南"

    def test_weight_ranking(self, index_db, sample_vault):
        index = MemoryIndex(index_db)
        scanner = VaultScanner(str(sample_vault))
        parser = MarkdownParser()
        for f in scanner.scan():
            index.upsert_file(f, parser.parse_file(f.path))

        # Docker 文件名匹配权重最高
        results = index.search("Docker")
        assert results[0]["title"] == "Docker优化笔记"
        assert results[0]["relevance"] >= 0.5

    def test_tag_search(self, index_db, sample_vault):
        index = MemoryIndex(index_db)
        scanner = VaultScanner(str(sample_vault))
        parser = MarkdownParser()
        for f in scanner.scan():
            index.upsert_file(f, parser.parse_file(f.path))

        results = index.search_by_tag("Docker")
        assert len(results) == 1
        assert "Docker" in results[0]["tags"]

    def test_hash_change_detection(self, index_db, sample_vault):
        index = MemoryIndex(index_db)
        scanner = VaultScanner(str(sample_vault))
        files = scanner.scan()
        index.bulk_update(files)

        # 无变化时 bulk_update 返回 0
        unchanged = scanner.scan()
        assert index.bulk_update(unchanged) == 0

        # 修改文件后应检测到变化
        target = sample_vault / "Docker优化笔记.md"
        target.write_text("# Docker优化笔记 v2\n\n更新内容。\n\n#Docker", encoding="utf-8")
        changed = scanner.scan()
        assert index.bulk_update(changed) >= 1

    def test_schema_version(self, index_db):
        index = MemoryIndex(index_db)
        stats = index.get_stats()
        assert stats["schema_version"] == SCHEMA_VERSION

    def test_reinit_preserves_data(self, index_db, sample_vault):
        index = MemoryIndex(index_db)
        scanner = VaultScanner(str(sample_vault))
        parser = MarkdownParser()
        for f in scanner.scan():
            index.upsert_file(f, parser.parse_file(f.path))

        # 重新初始化不应丢失数据
        index2 = MemoryIndex(index_db)
        stats = index2.get_stats()
        assert stats["total_indexed"] == 3