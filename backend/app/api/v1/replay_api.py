"""Context & Replay API - Phase 5.11"""
from fastapi import APIRouter

from app.intelligence.context.snapshot import get_snapshot_store, ContextSnapshot
from app.replay.replayer import get_replayer

router = APIRouter(prefix="", tags=["replay"])


@router.get("/tasks/{task_id}/context")
async def get_task_context(task_id: str):
    store = get_snapshot_store()
    snapshot = store.get(task_id)
    if not snapshot:
        return {"success": False, "error": "No context snapshot found"}
    return {"success": True, "context": snapshot.to_dict()}


@router.post("/tasks/{task_id}/replay")
async def replay_task(task_id: str):
    replayer = get_replayer()
    result = await replayer.replay(task_id)
    return {"success": True, "result": result.to_dict()}
