"""
Obsidian 知识库扫描器
扫描指定目录下的所有 .md 文件，支持增量扫描和 hash 变化检测。
"""

import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

# 默认忽略的目录和文件
IGNORE_DIRS = {".obsidian", ".git", ".trash", ".stversions", "node_modules", "__pycache__"}
IGNORE_PREFIXES = ("~$", ".")


@dataclass
class MarkdownFile:
    """表示一个 Markdown 文件的元信息"""
    path: str                    # 完整文件路径
    relative_path: str           # 相对于知识库根目录的路径
    name: str                    # 文件名
    title: str                   # 标题 (从文件名或首个 H1 提取)
    folder: str                  # 所属文件夹
    size: int                    # 文件大小 (bytes)
    modified_at: datetime        # 最后修改时间
    content_hash: str = ""       # 文件内容 hash (用于增量扫描)
    tags: list[str] = field(default_factory=list)


class VaultScanner:
    """
    Obsidian 知识库扫描器
    递归扫描指定目录，收集所有 .md 文件的元信息。
    支持增量扫描：通过 hash 检测文件变化。
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self._last_scan: dict[str, MarkdownFile] = {}  # path -> MarkdownFile
        if not self.vault_path.exists():
            logger.warning("Vault path does not exist", path=vault_path)

    def scan(self, incremental: bool = False) -> list[MarkdownFile]:
        """
        扫描知识库
        Args:
            incremental: 是否增量扫描 (只返回变化的文件)
        Returns:
            MarkdownFile 列表
        """
        if not self.vault_path.exists():
            logger.error("Cannot scan: vault path not found", path=str(self.vault_path))
            return []

        current_files: dict[str, MarkdownFile] = {}
        changed_files: list[MarkdownFile] = []

        for root, dirs, files in os.walk(self.vault_path):
            # 过滤忽略目录
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith((".", "~"))]

            for fname in files:
                if not fname.endswith(".md"):
                    continue
                if any(fname.startswith(p) for p in IGNORE_PREFIXES):
                    continue

                full_path = Path(root) / fname
                rel_path = str(full_path.relative_to(self.vault_path))
                stat = full_path.stat()

                # 计算内容 hash
                content_hash = self._file_hash(str(full_path))

                md_file = MarkdownFile(
                    path=str(full_path),
                    relative_path=rel_path,
                    name=fname,
                    title=fname.removesuffix(".md"),
                    folder=str(Path(rel_path).parent) if str(Path(rel_path).parent) != "." else "",
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    content_hash=content_hash,
                )

                current_files[str(full_path)] = md_file

                # 增量检测
                if incremental:
                    old = self._last_scan.get(str(full_path))
                    if old is None or old.content_hash != content_hash:
                        changed_files.append(md_file)

        self._last_scan = current_files

        if incremental:
            logger.info("Incremental scan complete", total=len(current_files), changed=len(changed_files))
            return changed_files

        logger.info("Full scan complete", total=len(current_files), path=str(self.vault_path))
        return list(current_files.values())

    def scan_folder(self, subfolder: str) -> list[MarkdownFile]:
        """只扫描指定子文件夹"""
        target = self.vault_path / subfolder
        if not target.exists():
            logger.warning("Subfolder not found", folder=subfolder)
            return []
        original = self.vault_path
        self.vault_path = target
        results = self.scan()
        self.vault_path = original
        return results

    def find_by_name(self, keyword: str) -> list[MarkdownFile]:
        """按文件名关键词搜索"""
        all_files = self.scan()
        return [f for f in all_files if keyword.lower() in f.name.lower()]

    def _file_hash(self, file_path: str) -> str:
        """计算文件内容的 MD5 hash"""
        h = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:  # noqa: BLE001 — hash failure returns empty
            return ""