"""
MemoryStorage — 内存存储后端。

基于字典的内存存储，适合测试和临时数据。
数据在进程重启后丢失。
"""

import copy
from typing import Any

from app.storage.base import StorageBackend
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryStorage(StorageBackend):
    """
    内存存储后端。
    
    数据存储在 Python 字典中，进程生命周期内有效。
    所有读取返回深拷贝，避免引用泄露。
    """

    def __init__(self):
        self._data: dict[str, Any] = {}

    async def save(self, key: str, value: Any) -> None:
        """保存键值对（深拷贝存储）"""
        self._data[key] = copy.deepcopy(value)
        logger.debug("MemoryStorage saved", key=key)

    async def get(self, key: str) -> Any | None:
        """获取值（返回深拷贝）"""
        value = self._data.get(key)
        if value is None:
            return None
        return copy.deepcopy(value)

    async def delete(self, key: str) -> bool:
        """删除键值对"""
        if key in self._data:
            del self._data[key]
            logger.debug("MemoryStorage deleted", key=key)
            return True
        return False

    async def list_keys(self, prefix: str = "") -> list[str]:
        """列出指定前缀的所有键"""
        if not prefix:
            return list(self._data.keys())
        return [k for k in self._data if k.startswith(prefix)]

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._data

    async def count(self, prefix: str = "") -> int:
        """统计键数量"""
        if not prefix:
            return len(self._data)
        return sum(1 for k in self._data if k.startswith(prefix))

    def clear(self) -> None:
        """清空所有数据"""
        self._data.clear()