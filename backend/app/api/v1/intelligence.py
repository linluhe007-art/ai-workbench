"""
Intelligence API - Phase 5.1
Natural language command entry point with intent analysis.
"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.intelligence.command import CommandProcessor
from app.intelligence.router import CommandRouter
from app.runtime.manager import get_runtime
from app.api.v1.websocket import make_event, get_ws_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

# Singleton processor
_processor: CommandProcessor | None = None


def _make_ws_broadcast():
    """Create a ws_broadcast function that properly formats events for the WebSocket manager."""
    runtime = get_runtime()
    ws_manager = get_ws_manager()

    if hasattr(runtime, "_ws_manager") and runtime._ws_manager:

        async def _broadcast(event_type: str, data: dict | None = None) -> None:
            try:
                event_data = data or {}
                event = make_event(event_type, "system", event_data)
                await ws_manager.broadcast_all(event)
            except Exception:
                pass

        return _broadcast
    return None


def _get_processor() -> CommandProcessor:
    global _processor
    if _processor is None:
        runtime = get_runtime()

        async def _create_task(prompt: str, max_iterations: int = 3):
            return runtime.create_task(prompt, max_iterations)

        router_instance = CommandRouter(
            task_creator=_create_task,
            ws_broadcast=_make_ws_broadcast(),
        )
        _processor = CommandProcessor(router=router_instance)
    return _processor


class CommandRequest(BaseModel):
    prompt: str


@router.post("/command")
async def process_command(req: CommandRequest, background_tasks: BackgroundTasks):
    """
    Process a natural language command.
    Analyzes intent, classifies task type, creates a task.
    """
    processor = _get_processor()
    result = await processor.process(req.prompt)

    # Broadcast task_created_from_command event if task was created
    if result.task_id:
        try:
            ws_manager = get_ws_manager()
            event = make_event("task_created_from_command", result.task_id, {
                "intent": result.intent,
                "confidence": result.confidence,
            })
            await ws_manager.broadcast(result.task_id, event)
        except Exception:
            pass

        runtime = get_runtime()
        background_tasks.add_task(runtime.submit_task, result.task_id)

    return {
        "success": True,
        "intent": result.intent,
        "task_id": result.task_id,
        "classification": result.classification,
        "confidence": result.confidence,
        "created_at": result.created_at,
    }


@router.get("/history")
async def get_command_history():
    """Get recent command history."""
    processor = _get_processor()
    history = processor.get_history()
    return {"history": history, "total": len(history)}
