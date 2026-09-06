"""Model Management API - Phase 5.9"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.models.provider import ProviderType
from app.models.manager import get_model_manager
from app.models.router import get_model_router, PrivacyLevel
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


class ConfigureRequest(BaseModel):
    provider_type: str
    endpoint: str = ""
    api_key: str = ""
    priority: int = 0


class TestRequest(BaseModel):
    provider_type: str


class GenerateRequest(BaseModel):
    task_category: str = "chat"
    prompt: str
    privacy_level: str = "low"


@router.get("")
async def list_models():
    """List all available and configured models."""
    manager = get_model_manager()
    router = get_model_router()
    routing_table = router.get_routing_table()
    configs = manager.list_configs()
    available_models = manager.get_all_available_models()

    return {
        "success": True,
        "routing_table": routing_table,
        "configs": configs,
        "available_models": available_models,
    }


@router.post("/configure")
async def configure_model(req: ConfigureRequest):
    """Configure a model provider."""
    try:
        pt = ProviderType(req.provider_type)
    except ValueError:
        return {"success": False, "error": f"Unknown provider type: {req.provider_type}"}

    manager = get_model_manager()
    manager.configure(pt, endpoint=req.endpoint, api_key=req.api_key, priority=req.priority)

    return {
        "success": True,
        "provider_type": pt.value,
        "message": f"Provider {pt.value} configured",
    }


@router.post("/test")
async def test_model(req: TestRequest):
    """Test connection to a model provider."""
    try:
        pt = ProviderType(req.provider_type)
    except ValueError:
        return {"success": False, "error": f"Unknown provider type: {req.provider_type}"}

    manager = get_model_manager()
    ok = await manager.test_provider(pt)

    return {
        "success": True,
        "provider_type": pt.value,
        "connected": ok,
        "message": "Connection successful" if ok else "Connection failed",
    }


@router.post("/generate")
async def generate_with_model(req: GenerateRequest):
    """Generate text using the routed model."""
    router = get_model_router()
    pl = PrivacyLevel(req.privacy_level) if req.privacy_level else None
    result = await router.generate(req.task_category, req.prompt, privacy_level=pl)
    return {"success": True, **result}


@router.get("/providers")
async def list_providers():
    """List supported provider types."""
    return {
        "success": True,
        "providers": [
            {"type": pt.value, "description": _provider_description(pt)}
            for pt in ProviderType
        ],
    }


def _provider_description(pt: ProviderType) -> str:
    descriptions = {
        ProviderType.OLLAMA: "Local LLM via Ollama (http://localhost:11434)",
        ProviderType.LLAMA_CPP: "llama.cpp server (http://localhost:8080)",
        ProviderType.OPENAI_COMPATIBLE: "OpenAI-compatible API (vLLM, TGI, etc.)",
    }
    return descriptions.get(pt, "Unknown provider")
