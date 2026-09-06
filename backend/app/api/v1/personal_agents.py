"""Personal Agent Team API - Phase 5.5"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.personal_agents.manager import PersonalAgentManager
from app.personal_agents.selector import PersonalAgentSelector
from app.api.v1.websocket import make_event, get_ws_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["personal-agents"])

_manager: PersonalAgentManager | None = None
_selector: PersonalAgentSelector | None = None


def _get_manager() -> PersonalAgentManager:
    global _manager
    if _manager is None:
        _manager = PersonalAgentManager()
    return _manager


def _get_selector() -> PersonalAgentSelector:
    global _selector
    if _selector is None:
        _selector = PersonalAgentSelector(_get_manager())
    return _selector


class SelectRequest(BaseModel):
    task_type: str = ""
    capabilities: list[str] = []
    task_description: str = ""


@router.get("/personal")
async def list_personal_agents():
    manager = _get_manager()
    members = manager.list_members()
    stats = manager.get_team_stats()
    return {"success": True, "members": members, "stats": stats}


@router.post("/select")
async def select_agent(req: SelectRequest):
    selector = _get_selector()
    manager = _get_manager()

    task_type = req.task_type
    if not task_type and req.task_description:
        task_type = selector.get_best_role_for_task(req.task_description) or ""

    member = selector.select(
        task_type=task_type,
        required_capabilities=req.capabilities if req.capabilities else None,
    )

    result = {
        "success": member is not None,
        "task_type": task_type,
        "member": member.to_dict() if member else None,
    }

    if member:
        try:
            ws = get_ws_manager()
            event = make_event("agent_selected", "system", result)
            await ws.broadcast_all(event)
        except Exception:
            pass

    return result


@router.get("/personal/delegations")
async def get_delegations(limit: int = 50):
    manager = _get_manager()
    delegations = manager.get_delegations(limit=limit)
    return {"success": True, "delegations": delegations, "total": len(delegations)}


@router.get("/personal/roles")
async def get_roles():
    from app.personal_agents.roles import get_all_roles
    roles = get_all_roles()
    return {"success": True, "roles": [{"name": r.name, "role": r.role.value, "capabilities": r.capabilities, "tools": r.tools, "description": r.description} for r in roles]}
