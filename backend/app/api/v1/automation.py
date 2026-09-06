"""Automation API - Phase 5.6"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.automation.scheduler import AutomationScheduler, AutomationRule, AutomationStatus
from app.automation.trigger import Trigger, TriggerType
from app.automation.executor import AutomationExecutor
from app.api.v1.websocket import make_event, get_ws_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])

_scheduler: AutomationScheduler | None = None


def _get_scheduler() -> AutomationScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AutomationScheduler()
        _scheduler.start()
    return _scheduler


class CreateAutomationRequest(BaseModel):
    name: str
    description: str = ""
    trigger_type: str = "schedule"
    cron_expression: str = ""
    event_name: str = ""
    action_type: str = "create_task"
    action_params: dict = {}
    max_iterations: int = 3


@router.post("")
async def create_automation(req: CreateAutomationRequest):
    scheduler = _get_scheduler()
    ttype = TriggerType(req.trigger_type)
    trigger = Trigger(
        trigger_type=ttype,
        cron_expression=req.cron_expression,
        event_name=req.event_name,
    )
    action = {"type": req.action_type, "params": req.action_params}
    rule = scheduler.add_rule(req.name, trigger, action, req.description)
    return {"success": True, "automation": rule.to_dict()}


@router.get("")
async def list_automations():
    scheduler = _get_scheduler()
    rules = scheduler.list_rules()
    return {"success": True, "automations": rules, "total": len(rules)}


@router.get("/{automation_id}")
async def get_automation(automation_id: str):
    scheduler = _get_scheduler()
    rule = scheduler.get_rule(automation_id)
    if not rule:
        return {"success": False, "error": "Automation not found"}
    return {"success": True, "automation": rule.to_dict()}


@router.post("/{automation_id}/run")
async def run_automation(automation_id: str):
    scheduler = _get_scheduler()
    rule = scheduler.get_rule(automation_id)
    if not rule:
        return {"success": False, "error": "Automation not found"}

    try:
        ws = get_ws_manager()
        await ws.broadcast_all(make_event("automation_started", "system", {"automation_id": automation_id, "name": rule.name}))
    except Exception:
        pass

    log = await scheduler.run_rule(automation_id)

    try:
        ws = get_ws_manager()
        await ws.broadcast_all(make_event("automation_completed", "system", {"automation_id": automation_id, "status": log.status if log else "unknown"}))
    except Exception:
        pass

    return {"success": True, "log": log.to_dict() if log else None}


@router.put("/{automation_id}/status")
async def update_status(automation_id: str, status: str):
    scheduler = _get_scheduler()
    ok = scheduler.update_status(automation_id, status)
    return {"success": ok, "automation_id": automation_id, "status": status}


@router.delete("/{automation_id}")
async def delete_automation(automation_id: str):
    scheduler = _get_scheduler()
    ok = scheduler.remove_rule(automation_id)
    return {"success": ok}


@router.get("/{automation_id}/logs")
async def get_logs(automation_id: str, limit: int = 50):
    scheduler = _get_scheduler()
    executor = scheduler.get_executor()
    logs = executor.get_logs(automation_id=automation_id, limit=limit)
    return {"success": True, "logs": logs, "total": len(logs)}
