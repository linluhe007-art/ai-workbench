"""
Memory 本地索引
使用 SQLite + FTS5 全文索引，支持增量更新和加权搜索。
包含 schema version 机制，支持未来 migration。
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.memory.parser import MarkdownParser, ParsedDocument
from app.memory.scanner import MarkdownFile
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_INDEX_DB = "data/memory_index.db"
SCHEMA_VERSION = 1


class MemoryIndex:
    """
    Memory 本地索引 (SQLite + FTS5)
    特性：
    - FTS5 全文索引，替代 LIKE 模糊查询
    - Schema version 机制，支持未来 migration
    - 增量更新：只处理 hash 变化的文件
    - 加权评分搜索
    """

    def __init__(self, db_path: str = DEFAULT_INDEX_DB):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.parser = MarkdownParser()
        self._init_db()

    def _init_db(self):
        """初始化数据库：创建表、索引、FTS5 虚拟表"""
        with sqlite3.connect(self.db_path) as conn:
            # Schema version 表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)

            current = self._get_version(conn)
            if current < SCHEMA_VERSION:
                self._migrate(conn, current)

            conn.commit()

    def _get_version(self, conn: sqlite3.Connection) -> int:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return row[0] if row and row[0] else 0

    def _migrate(self, conn: sqlite3.Connection, from_version: int):
        """执行 migration"""
        logger.info("Migrating memory index", from_version=from_version, to_version=SCHEMA_VERSION)

        if from_version < 1:
            # V1: 主表 + FTS5
            conn.execute("""
                CREATE TABLE IF NOT EXISTS markdown_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    relative_path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    folder TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    keywords TEXT DEFAULT '[]',
                    wikilinks TEXT DEFAULT '[]',
                    summary TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    hash TEXT DEFAULT '',
                    size INTEGER DEFAULT 0,
                    updated_time TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON markdown_files(path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_folder ON markdown_files(folder)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON markdown_files(hash)")

            # FTS5 虚拟表
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title,
                    tags,
                    content,
                    content=markdown_files,
                    content_rowid=id
                )
            """)

            # FTS5 同步触发器
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS markdown_files_ai AFTER INSERT ON markdown_files BEGIN
                    INSERT INTO documents_fts(rowid, title, tags, content)
                    VALUES (new.id, new.title, new.tags, new.content);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS markdown_files_ad AFTER DELETE ON markdown_files BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, title, tags, content)
                    VALUES ('delete', old.id, old.title, old.tags, old.content);
                END
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS markdown_files_au AFTER UPDATE ON markdown_files BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, title, tags, content)
                    VALUES ('delete', old.id, old.title, old.tags, old.content);
                    INSERT INTO documents_fts(rowid, title, tags, content)
                    VALUES (new.id, new.title, new.tags, new.content);
                END
            """)

        conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (SCHEMA_VERSION, datetime.now(timezone.utc).isoformat()),
        )
        logger.info("Migration complete", version=SCHEMA_VERSION)

    def upsert_file(self, md_file: MarkdownFile, doc: ParsedDocument):
        """插入或更新单个文件索引 (自动同步 FTS5)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO markdown_files (path, relative_path, title, folder, tags, keywords, wikilinks, summary, content, hash, size, updated_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    title=excluded.title,
                    folder=excluded.folder,
                    tags=excluded.tags,
                    keywords=excluded.keywords,
                    wikilinks=excluded.wikilinks,
                    summary=excluded.summary,
                    content=excluded.content,
                    hash=excluded.hash,
                    size=excluded.size,
                    updated_time=excluded.updated_time
            """, (
                md_file.path, md_file.relative_path, doc.title, md_file.folder,
                json.dumps(doc.tags, ensure_ascii=False),
                json.dumps(doc.keywords, ensure_ascii=False),
                json.dumps(doc.wikilinks, ensure_ascii=False),
                doc.summary, doc.full_text[:10000],
                md_file.content_hash, md_file.size,
                datetime.now(timezone.utc).isoformat(),
            ))
            conn.commit()

    def bulk_update(self, files: list[MarkdownFile]) -> int:
        """批量更新：只处理 hash 变化的文件"""
        updated = 0
        for md_file in files:
            if self._needs_update(md_file.path, md_file.content_hash):
                doc = self.parser.parse_file(md_file.path)
                self.upsert_file(md_file, doc)
                updated += 1
        if updated > 0:
            logger.info("Index updated", files_updated=updated)
        return updated

    def _needs_update(self, path: str, content_hash: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT hash FROM markdown_files WHERE path = ?", (path,)
            ).fetchone()
            return row is None or row[0] != content_hash

    def search(self, keyword: str, limit: int = 10) -> list[dict]:
        """
        FTS5 全文搜索 + 加权评分
        权重：filename +0.5, title +0.3, tags +0.2, content(FTS) 排序
        """
        results = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # FTS5 搜索获取候选集 (按相关性排序)
            try:
                fts_rows = conn.execute("""
                    SELECT rowid, rank FROM documents_fts
                    WHERE documents_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (keyword, limit * 3)).fetchall()
                fts_ids = {r["rowid"]: r["rank"] for r in fts_rows}
            except sqlite3.OperationalError:
                # FTS 表为空或查询语法错误，降级到精确匹配
                fts_ids = {}

            if fts_ids:
                placeholders = ",".join("?" * len(fts_ids))
                rows = conn.execute(
                    f"SELECT * FROM markdown_files WHERE id IN ({placeholders})",
                    list(fts_ids.keys())
                ).fetchall()
            else:
                # 降级：全表扫描 (仅在 FTS 不可用时)
                rows = conn.execute("SELECT * FROM markdown_files").fetchall()

            keyword_lower = keyword.lower()
            for row in rows:
                score = 0.0

                # 文件名匹配 +0.5
                if keyword_lower in Path(row["relative_path"]).stem.lower():
                    score += 0.5

                # 标题匹配 +0.3
                if keyword_lower in row["title"].lower():
                    score += 0.3

                # 标签匹配 +0.2
                try:
                    tags = json.loads(row["tags"])
                    if any(keyword_lower in t.lower() for t in tags):
                        score += 0.2
                except (json.JSONDecodeError, TypeError):
                    pass

                # FTS 匹配 +0.1 (存在即加分)
                if row["id"] in fts_ids:
                    score += 0.1

                if score > 0:
                    results.append({
                        "path": row["relative_path"],
                        "title": row["title"],
                        "folder": row["folder"],
                        "tags": json.loads(row["tags"]) if row["tags"] else [],
                        "wikilinks": json.loads(row["wikilinks"]) if row["wikilinks"] else [],
                        "keywords": json.loads(row["keywords"]) if row["keywords"] else [],
                        "summary": row["summary"],
                        "relevance": round(score, 2),
                    })

        results.sort(key=lambda r: r["relevance"], reverse=True)
        return results[:limit]

    def search_by_tag(self, tag: str, limit: int = 10) -> list[dict]:
        """按标签精确搜索"""
        results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM markdown_files").fetchall()
            for row in rows:
                try:
                    tags = json.loads(row["tags"])
                    if tag in tags:
                        results.append({
                            "path": row["relative_path"],
                            "title": row["title"],
                            "folder": row["folder"],
                            "tags": tags,
                            "summary": row["summary"],
                            "relevance": 1.0,
                        })
                except (json.JSONDecodeError, TypeError):
                    continue
        return results[:limit]

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM markdown_files").fetchone()[0]
            folders = conn.execute("SELECT DISTINCT folder FROM markdown_files").fetchall()
            version = self._get_version(conn)
            return {
                "total_indexed": total,
                "folders": [f[0] for f in folders if f[0]],
                "schema_version": version,
            }

    def remove_file(self, path: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM markdown_files WHERE path = ?", (path,))
            conn.commit()