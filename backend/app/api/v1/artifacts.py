"""Artifacts API - CRUD for task artifacts."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["artifacts"])


class RenameRequest(BaseModel):
    """Request body for artifact rename."""
    name: str = Field(..., min_length=1, max_length=200)


@router.get("/tasks/{task_id}/artifacts")
async def get_task_artifacts(task_id: str):
    """Get all artifacts produced by a task."""
    runtime = get_runtime()
    record = runtime.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found")

    items = runtime.workspace_manager.list_items(task_id)
    return {
        "task_id": task_id,
        "artifacts": [item.to_dict() for item in items],
        "total": len(items),
    }


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str):
    """Get a single artifact by ID. Searches across all workspaces."""
    runtime = get_runtime()
    result = runtime.workspace_manager.find_item_globally(artifact_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    workspace_id, item = result
    data = item.to_dict()
    data["workspace_id"] = workspace_id
    return data


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(artifact_id: str):
    """Delete an artifact by ID. Searches across all workspaces."""
    runtime = get_runtime()
    result = runtime.workspace_manager.find_item_globally(artifact_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    workspace_id, item = result
    runtime.workspace_manager.delete_item(workspace_id, artifact_id)
    logger.info("Artifact deleted", artifact_id=artifact_id, workspace_id=workspace_id)
    return {"deleted": True, "artifact_id": artifact_id, "workspace_id": workspace_id}


@router.post("/artifacts/{artifact_id}/rename")
async def rename_artifact(artifact_id: str, req: RenameRequest):
    """Rename an artifact."""
    runtime = get_runtime()
    result = runtime.workspace_manager.find_item_globally(artifact_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    workspace_id, _item = result
    updated = runtime.workspace_manager.rename_item(workspace_id, artifact_id, req.name)
    if updated is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    logger.info("Artifact renamed", artifact_id=artifact_id, new_name=req.name)
    return updated.to_dict()