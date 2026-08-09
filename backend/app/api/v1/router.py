from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.memory import router as memory_router
from app.api.v1.orchestrator import router as orchestrator_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(orchestrator_router)
api_router.include_router(memory_router)