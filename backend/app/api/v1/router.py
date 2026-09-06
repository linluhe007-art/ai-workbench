from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.memory import router as memory_router
from app.api.v1.orchestrator import router as orchestrator_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.agents import router as agents_router
from app.api.v1.executions import router as executions_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.agent_management import router as agent_management_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.planning import router as planning_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.artifact_search import router as artifact_search_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.system import router as system_router
from app.api.v1.agent_lifecycle import router as agent_lifecycle_router
from app.api.v1.experience import router as experience_router
from app.api.v1.openapi import router as openapi_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.metrics_api import router as metrics_api_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.personal_agents import router as personal_agents_router
from app.api.v1.automation import router as automation_router
from app.api.v1.personal import router as personal_router
from app.api.v1.improvement import router as improvement_router
from app.api.v1.models_api import router as models_api_router
from app.api.v1.os_api import router as os_api_router
from app.api.v1.trace_api import router as trace_api_router
from app.api.v1.prompts_api import router as prompts_api_router
from app.api.v1.analytics_api import router as analytics_api_router
from app.api.v1.replay_api import router as replay_api_router

from app.api.v1.research import router as research_router
from app.api.v1.llm import router as llm_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(orchestrator_router)
api_router.include_router(memory_router)
api_router.include_router(tasks_router)
api_router.include_router(agents_router)
api_router.include_router(agent_management_router)
api_router.include_router(executions_router)
api_router.include_router(websocket_router)
api_router.include_router(workspaces_router)
api_router.include_router(workflows_router)
api_router.include_router(planning_router)
api_router.include_router(artifacts_router)
api_router.include_router(artifact_search_router)
api_router.include_router(audit_router)
api_router.include_router(auth_router)
api_router.include_router(system_router)
api_router.include_router(agent_lifecycle_router)
api_router.include_router(experience_router)
api_router.include_router(openapi_router)
api_router.include_router(intelligence_router)
api_router.include_router(metrics_api_router)
api_router.include_router(knowledge_router)
api_router.include_router(personal_agents_router)
api_router.include_router(automation_router)
api_router.include_router(personal_router)
api_router.include_router(improvement_router)
api_router.include_router(models_api_router)
api_router.include_router(os_api_router)
api_router.include_router(trace_api_router)
api_router.include_router(prompts_api_router)
api_router.include_router(analytics_api_router)
api_router.include_router(replay_api_router)
api_router.include_router(research_router)
api_router.include_router(llm_router)
