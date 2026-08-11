from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.memory import router as memory_router
from app.api.v1.orchestrator import router as orchestrator_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.agents import router as agents_router
from app.api.v1.executions import router as executions_router
from app.api.v1.websocket import router as websocket_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(orchestrator_router)
api_router.include_router(memory_router)
api_router.include_router(tasks_router)
api_router.include_router(agents_router)
api_router.include_router(executions_router)
api_router.include_router(websocket_router)