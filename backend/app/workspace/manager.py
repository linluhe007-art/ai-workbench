"""
WorkspaceManager — 工作空间管理器。

管理多任务共享工作空间的生命周期和访问。
不同 Agent 可在同一 workspace 中读写产物，实现协作。
"""

from app.workspace.models import WorkspaceItem
from app.workspace.storage import InMemoryStorage
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WorkspaceManager:
    """
    工作空间管理器。

    职责：
    - 创建 / 销毁工作空间
    - 添加 / 查询 / 删除条目
    - 为 Agent 提供便捷读写接口
    """

    def __init__(self, storage: InMemoryStorage | None = None):
        self._storage = storage or InMemoryStorage()

    def create_workspace(self, task_id: str) -> str:
        """
        创建工作空间。
        Args:
            task_id: 任务 ID（用作 workspace_id）
        Returns:
            workspace_id
        """
        self._storage.create_workspace(task_id)
        return task_id

    def add_item(self, workspace_id: str, item: WorkspaceItem) -> WorkspaceItem:
        """
        向工作空间添加条目。
        Args:
            workspace_id: 工作空间 ID
            item: WorkspaceItem 实例
        Returns:
            写入后的 item
        """
        return self._storage.add_item(workspace_id, item)

    def get_item(self, workspace_id: str, item_id: str) -> WorkspaceItem | None:
        """
        获取单个条目。
        Args:
            workspace_id: 工作空间 ID
            item_id: 条目 ID
        Returns:
            WorkspaceItem 或 None
        """
        return self._storage.get_item(workspace_id, item_id)

    def list_items(self, workspace_id: str) -> list[WorkspaceItem]:
        """
        列出工作空间所有条目。
        Args:
            workspace_id: 工作空间 ID
        Returns:
            WorkspaceItem 列表
        """
        return self._storage.list_items(workspace_id)

    def delete_item(self, workspace_id: str, item_id: str) -> bool:
        """
        删除条目。
        Args:
            workspace_id: 工作空间 ID
            item_id: 条目 ID
        Returns:
            是否成功删除
        """
        return self._storage.delete_item(workspace_id, item_id)

    def save_artifact(
        self,
        workspace_id: str,
        owner: str,
        name: str,
        content: any,
        item_type: str = "text",
        metadata: dict | None = None,
    ) -> WorkspaceItem:
        """
        Agent 保存产物的便捷方法。
        自动创建 WorkspaceItem 并写入。
        """
        item = WorkspaceItem(
            name=name,
            type=item_type,
            content=content,
            owner=owner,
            metadata=metadata or {},
        )
        return self.add_item(workspace_id, item)

    def get_artifacts_by_owner(self, workspace_id: str, owner: str) -> list[WorkspaceItem]:
        """
        获取指定 Agent 的所有产物。
        Args:
            workspace_id: 工作空间 ID
            owner: Agent ID
        Returns:
            WorkspaceItem 列表
        """
        items = self.list_items(workspace_id)
        return [i for i in items if i.owner == owner]

    def get_artifacts_by_type(self, workspace_id: str, item_type: str) -> list[WorkspaceItem]:
        """
        获取指定类型的所有产物。
        """
        items = self.list_items(workspace_id)
        return [i for i in items if i.type == item_type]