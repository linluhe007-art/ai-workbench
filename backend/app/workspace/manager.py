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

    def find_item_globally(self, item_id: str) -> tuple[str, WorkspaceItem] | None:
        """Search all workspaces for an item by ID. Returns (workspace_id, item) or None."""
        for ws_id, items in self._storage._store.items():
            if item_id in items:
                return (ws_id, items[item_id])
        return None

    def update_item_metadata(self, workspace_id: str, item_id: str, metadata: dict) -> WorkspaceItem | None:
        """Merge new metadata fields into an existing item."""
        item = self.get_item(workspace_id, item_id)
        if item is None:
            return None
        item.metadata.update(metadata)
        return item

    def rename_item(self, workspace_id: str, item_id: str, new_name: str) -> WorkspaceItem | None:
        """Rename an artifact. Returns updated item or None if not found."""
        item = self.get_item(workspace_id, item_id)
        if item is None:
            return None
        item.name = new_name
        return item

    def get_all_workspaces(self) -> list[str]:
        """List all workspace IDs."""
        return list(self._storage._store.keys())

    def search_items(
        self,
        query: str | None = None,
        artifact_type: str | None = None,
        agent_id: str | None = None,
        task_id: str | None = None,
        workspace_id: str | None = None,
        step_id: str | None = None,
        created_after: object | None = None,
        created_before: object | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Search artifacts across workspaces with filters, sorting, pagination."""
        # Collect candidate items
        candidates: list[tuple[str, WorkspaceItem]] = []

        if workspace_id:
            # Restrict to specific workspace
            for item in self.list_items(workspace_id):
                candidates.append((workspace_id, item))
        elif task_id:
            # task_id maps to workspace_id
            for item in self.list_items(task_id):
                candidates.append((task_id, item))
        else:
            # Search all workspaces
            for ws_id in self.get_all_workspaces():
                for item in self.list_items(ws_id):
                    candidates.append((ws_id, item))

        # Apply filters
        results: list[tuple[str, WorkspaceItem]] = []
        query_lower = query.lower() if query else None

        for ws_id, item in candidates:
            # Type filter
            if artifact_type and item.type != artifact_type:
                continue
            # Agent filter
            if agent_id:
                item_agent = (item.metadata.get("created_by") or item.owner)
                if item_agent != agent_id:
                    continue
            # Step filter
            if step_id:
                if item.metadata.get("step_id") != step_id:
                    continue
            # Date filters
            if created_after and item.created_at < created_after:
                continue
            if created_before and item.created_at > created_before:
                continue
            # Text query
            if query_lower:
                name_match = query_lower in item.name.lower()
                content_str = item.content if isinstance(item.content, str) else str(item.content)
                content_match = query_lower in content_str.lower()
                if not name_match and not content_match:
                    continue
            results.append((ws_id, item))

        # Sort
        def sort_key(entry: tuple[str, WorkspaceItem]):
            _, item = entry
            if sort_by == "name":
                return item.name.lower()
            elif sort_by == "type":
                return item.type
            else:  # created_at
                return item.created_at.isoformat()

        reverse = (order == "desc")
        results.sort(key=sort_key, reverse=reverse)

        total = len(results)
        paginated = results[offset:offset + limit]

        items_out = []
        for ws_id, item in paginated:
            d = item.to_dict()
            d["workspace_id"] = ws_id
            items_out.append(d)

        return items_out, total