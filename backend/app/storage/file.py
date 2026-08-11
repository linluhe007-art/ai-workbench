"""
FileStorage — JSON 文件存储后端。

数据以 JSON 文件形式持久化到文件系统。
每个 key 对应一个 .json 文件。
支持前缀扫描和批量操作。
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.storage.base import StorageBackend
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FileStorage(StorageBackend):
    """
    JSON 文件存储后端。
    
    数据按 key 映射到文件系统：
    - key 中的 ":" 替换为 "/" 作为子目录
    - 每个 key 存储为一个 .json 文件
    
    例如：
    - key "agent:mock-1" -> {base_dir}/agent/mock-1.json
    - key "exec:task-abc" -> {base_dir}/exec/task-abc.json
    """

    def __init__(self, base_dir: str | Path):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, key: str) -> Path:
        """将 key 转换为文件路径"""
        # 将 : 替换为路径分隔符
        parts = key.replace(":", "/")
        path = self._base_dir / f"{parts}.json"
        return path

    def _path_to_key(self, path: Path) -> str:
        """将文件路径转换回 key"""
        rel = path.relative_to(self._base_dir)
        # 去掉 .json 后缀
        key = str(rel.with_suffix(""))
        # 将路径分隔符替换回 :
        key = key.replace(os.sep, "/").replace("/", ":")
        return key

    async def save(self, key: str, value: Any) -> None:
        """保存键值对到 JSON 文件"""
        path = self._key_to_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "key": key,
            "value": value,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.debug("FileStorage saved", key=key, path=str(path))

    async def get(self, key: str) -> Any | None:
        """从 JSON 文件获取值"""
        path = self._key_to_path(key)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("value")
        except (json.JSONDecodeError, OSError) as e:  # noqa: BLE001
            logger.warning("FileStorage read error", key=key, error=str(e))
            return None

    async def delete(self, key: str) -> bool:
        """删除 JSON 文件"""
        path = self._key_to_path(key)
        if path.exists():
            path.unlink()
            logger.debug("FileStorage deleted", key=key)
            return True
        return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        """列出指定前缀的所有键"""
        keys = []
        for json_file in self._base_dir.rglob("*.json"):
            key = self._path_to_key(json_file)
            if not prefix or key.startswith(prefix):
                keys.append(key)
        return sorted(keys)

    async def exists(self, key: str) -> bool:
        """检查键对应的文件是否存在"""
        return self._key_to_path(key).exists()

    async def count(self, prefix: str = "") -> int:
        """统计键数量"""
        keys = await self.list_keys(prefix)
        return len(keys)