"""
InMemoryStorage — 工作空间内存存储。

提供 WorkspaceItem 的 CRUD 操作。
以 workspace_id 为命名空间隔离不同任务的工作空间。
"""

from app.workspace.models import WorkspaceItem
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InMemoryStorage:
    """
    内存存储后端。
    以 dict 嵌套结构存储：{workspace_id: {item_id: WorkspaceItem}}。
    当前为内存实现，未来可替换为持久化存储。
    """

    def __init__(self):
        self._store: dict[str, dict[str, WorkspaceItem]] = {}

    def create_workspace(self, workspace_id: str) -> None:
        """创建工作空间（幂等）"""
        if workspace_id not in self._store:
            self._store[workspace_id] = {}
            logger.info("Workspace created", workspace_id=workspace_id)

    def add_item(self, workspace_id: str, item: WorkspaceItem) -> WorkspaceItem:
        """添加条目到工作空间"""
        if workspace_id not in self._store:
            self._store[workspace_id] = {}
        self._store[workspace_id][item.id] = item
        logger.debug("Item added", workspace=workspace_id, item_id=item.id, name=item.name)
        return item

    def get_item(self, workspace_id: str, item_id: str) -> WorkspaceItem | None:
        """获取单个条目"""
        ws = self._store.get(workspace_id, {})
        return ws.get(item_id)

    def list_items(self, workspace_id: str) -> list[WorkspaceItem]:
        """列出工作空间所有条目"""
        ws = self._store.get(workspace_id, {})
        return list(ws.values())

    def delete_item(self, workspace_id: str, item_id: str) -> bool:
        """删除条目，返回是否成功"""
        ws = self._store.get(workspace_id, {})
        if item_id in ws:
            del ws[item_id]
            logger.debug("Item deleted", workspace=workspace_id, item_id=item_id)
            return True
        return False

    def workspace_exists(self, workspace_id: str) -> bool:
        """检查工作空间是否存在"""
        return workspace_id in self._store

    def clear(self) -> None:
        """清空所有数据（测试用）"""
        self._store.clear()