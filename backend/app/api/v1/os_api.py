"""Personal AI OS API - Phase 5.10"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.os.orchestrator import get_orchestrator, OrchestrationResult
from app.os.context import get_context_builder
from app.os.decision import get_decision_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/os", tags=["os"])


class ProcessIntentRequest(BaseModel):
    intent: str
    task_category: str = ""


class OSStatusResponse(BaseModel):
    success: bool = True
    os_version: str = "5.10"
    components: dict = {
        "orchestrator": "active",
        "context_builder": "active",
        "decision_engine": "active",
    }
    system_health: str = "healthy"


@router.post("/process")
async def process_intent(req: ProcessIntentRequest):
    """Process user intent through the full AI OS pipeline."""
    if not req.intent.strip():
        return {"success": False, "error": "Intent is required"}

    orchestrator = get_orchestrator()
    result = await orchestrator.process(req.intent, task_category=req.task_category)
    return {"success": True, "result": result.to_dict()}


@router.get("/status")
async def get_os_status():
    """Get the current status of the AI OS."""
    ctx_builder = get_context_builder()
    dec_engine = get_decision_engine()
    orchestrator = get_orchestrator()

    # Build a quick system context
    context = await ctx_builder.build(user_intent="status_check")
    state = context.system_state

    return {
        "success": True,
        "os_version": "5.10",
        "components": {
            "orchestrator": "active",
            "context_builder": "active",
            "decision_engine": "active",
        },
        "system_state": state.to_dict(),
        "agents_available": state.agents_available,
        "agents_active": state.agents_active,
        "tasks_running": state.tasks_running,
        "tasks_queued": state.tasks_queued,
        "overall_health": state.overall_health,
    }


@router.get("/insights")
async def get_os_insights():
    """Get AI OS insights and suggestions."""
    ctx_builder = get_context_builder()
    dec_engine = get_decision_engine()

    context = await ctx_builder.build()
    decision = dec_engine.decide(context)

    return {
        "success": True,
        "context": context.to_dict(),
        "decision": decision.to_dict(),
        "suggestions": [
            {"type": "tip", "message": "Use /os to see your AI at work"},
            {"type": "status", "message": f"{context.system_state.agents_available} agents available"},
            {"type": "action", "message": "Try the Command Center for natural language tasks"},
        ],
    }
