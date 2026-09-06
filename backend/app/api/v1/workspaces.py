"""
Workspaces API — 工作空间与 Artifact 管理。

POST   /api/v1/workspaces                         — 创建工作空间
GET    /api/v1/workspaces/{id}/items               — 列出所有 Artifact
GET    /api/v1/workspaces/{id}/items/{item_id}     — 获取单个 Artifact
DELETE /api/v1/workspaces/{id}/items/{item_id}     — 删除 Artifact
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.workspace.manager import WorkspaceManager
from app.workspace.models import WorkspaceItem
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

# 全局 WorkspaceManager 实例
_ws_manager: WorkspaceManager | None = None


def _get_ws_manager() -> WorkspaceManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WorkspaceManager()
    return _ws_manager


def reset_ws_manager() -> None:
    """重置（仅用于测试）"""
    global _ws_manager
    _ws_manager = None


# ── Request/Response Models ─────────────────────────────────


class WorkspaceCreateRequest(BaseModel):
    """创建工作空间请求"""
    task_id: str = Field(..., min_length=1, description="任务 ID")


class ItemCreateRequest(BaseModel):
    """添加 Artifact 请求"""
    name: str = Field(..., min_length=1, description="Artifact 名称")
    type: str = Field(default="text", description="类型: text / dict / list / image_url")
    content: Any = Field(default=None, description="内容")
    owner: str = Field(default="user", description="创建者 Agent ID")
    metadata: dict = Field(default_factory=dict)


# ── Routes ──────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_workspace(req: WorkspaceCreateRequest):
    """创建工作空间"""
    mgr = _get_ws_manager()
    ws_id = mgr.create_workspace(req.task_id)
    logger.info("Workspace created via API", workspace_id=ws_id)
    return {"workspace_id": ws_id, "task_id": req.task_id}


@router.post("/{workspace_id}/items", status_code=201)
async def add_item(workspace_id: str, req: ItemCreateRequest):
    """向工作空间添加 Artifact"""
    mgr = _get_ws_manager()
    item = WorkspaceItem(
        name=req.name,
        type=req.type,
        content=req.content,
        owner=req.owner,
        metadata=req.metadata,
    )
    result = mgr.add_item(workspace_id, item)
    return result.to_dict()


@router.get("/{workspace_id}/items")
async def list_items(workspace_id: str):
    """列出工作空间所有 Artifact"""
    mgr = _get_ws_manager()
    items = mgr.list_items(workspace_id)
    return {
        "workspace_id": workspace_id,
        "items": [i.to_dict() for i in items],
        "total": len(items),
    }


@router.get("/{workspace_id}/items/{item_id}")
async def get_item(workspace_id: str, item_id: str):
    """获取单个 Artifact"""
    mgr = _get_ws_manager()
    item = mgr.get_item(workspace_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.to_dict()


@router.delete("/{workspace_id}/items/{item_id}")
async def delete_item(workspace_id: str, item_id: str):
    """删除 Artifact"""
    mgr = _get_ws_manager()
    deleted = mgr.delete_item(workspace_id, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted": True, "item_id": item_id}