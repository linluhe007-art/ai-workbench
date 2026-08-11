"""
Storage — 抽象存储接口。

定义统一的键值存储接口，供 MemoryStorage 和 FileStorage 实现。
"""

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """
    存储后端抽象接口。
    
    所有存储实现必须继承此类。
    键采用 "prefix:key" 的分层命名约定。
    """

    @abstractmethod
    async def save(self, key: str, value: Any) -> None:
        """
        保存键值对。
        Args:
            key: 存储键（如 "agent:mock-1", "exec:task-abc"）
            value: 可 JSON 序列化的值
        """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        获取值。
        Args:
            key: 存储键
        Returns:
            存储的值，不存在返回 None
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        删除键值对。
        Args:
            key: 存储键
        Returns:
            True 如果键存在并被删除，False 如果键不存在
        """

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        列出指定前缀的所有键。
        Args:
            prefix: 键前缀（如 "agent:", "exec:"）
        Returns:
            匹配的键列表
        """

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return (await self.get(key)) is not None

    async def save_many(self, items: dict[str, Any]) -> int:
        """
        批量保存。
        Args:
            items: {key: value} 字典
        Returns:
            成功保存的数量
        """
        count = 0
        for key, value in items.items():
            await self.save(key, value)
            count += 1
        return count

    async def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        批量获取。
        Args:
            keys: 键列表
        Returns:
            {key: value} 字典，不包含不存在的键
        """
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def count(self, prefix: str = "") -> int:
        """统计指定前缀的键数量"""
        keys = await self.list_keys(prefix)
        return len(keys)