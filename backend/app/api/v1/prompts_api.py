"""Prompt Registry API - Phase 5.11"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.prompts.manager import get_prompt_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/prompts", tags=["prompts"])


class CreatePromptRequest(BaseModel):
    name: str
    content: str
    variables: list[str] = []
    description: str = ""


@router.post("")
async def create_prompt(req: CreatePromptRequest):
    mgr = get_prompt_manager()
    result = mgr.create_prompt(req.name, req.content, req.variables, req.description)
    return {"success": True, "prompt": result}


@router.get("")
async def list_prompts():
    mgr = get_prompt_manager()
    prompts = mgr.list_prompts()
    return {"success": True, "prompts": prompts, "total": len(prompts)}


@router.get("/{name}")
async def get_prompt(name: str):
    mgr = get_prompt_manager()
    prompt = mgr.get_prompt(name)
    if not prompt:
        return {"success": False, "error": "Prompt not found"}
    return {"success": True, "prompt": prompt}


@router.post("/{name}/activate")
async def activate_prompt_version(name: str, version: int = 1):
    mgr = get_prompt_manager()
    ok = mgr.activate_version(name, version)
    return {"success": ok, "name": name, "version": version}
