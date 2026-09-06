"""Automation Executor - Phase 5.6"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExecutionLog:
    id: str = ""
    automation_id: str = ""
    status: str = "pending"
    result: dict = field(default_factory=dict)
    error: str = ""
    started_at: str = ""
    finished_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "automation_id": self.automation_id,
            "status": self.status, "result": self.result, "error": self.error,
            "started_at": self.started_at, "finished_at": self.finished_at,
            "created_at": self.created_at,
        }


class AutomationExecutor:
    def __init__(self, task_creator=None):
        self._task_creator = task_creator
        self._execution_logs: dict[str, ExecutionLog] = {}
        self._automation_handlers: dict[str, callable] = {}

    def register_handler(self, action_type: str, handler):
        self._automation_handlers[action_type] = handler

    async def execute(self, automation: dict) -> ExecutionLog:
        import uuid
        log_id = str(uuid.uuid4())
        log = ExecutionLog(id=log_id, automation_id=automation.get("id", ""), status="running", started_at=datetime.now(timezone.utc).isoformat())
        self._execution_logs[log_id] = log

        try:
            action = automation.get("action", {})
            action_type = action.get("type", "create_task")

            if action_type in self._automation_handlers:
                result = await self._automation_handlers[action_type](automation)
            elif self._task_creator:
                task_desc = automation.get("description", automation.get("name", ""))
                result = await self._task_creator(task_desc, automation.get("max_iterations", 3))
            else:
                result = {"note": "No task creator configured", "automation": automation.get("name", "")}

            log.status = "completed"
            log.result = result if isinstance(result, dict) else {"output": str(result)}
            log.finished_at = datetime.now(timezone.utc).isoformat()
            logger.info("Automation executed", id=log_id, status="completed")
        except Exception as e:
            log.status = "failed"
            log.error = str(e)
            log.finished_at = datetime.now(timezone.utc).isoformat()
            logger.error("Automation failed", id=log_id, error=str(e))

        return log

    def get_logs(self, automation_id: str = "", limit: int = 50) -> list[dict]:
        logs = list(self._execution_logs.values())
        if automation_id:
            logs = [l for l in logs if l.automation_id == automation_id]
        logs.sort(key=lambda l: l.created_at, reverse=True)
        return [l.to_dict() for l in logs[:limit]]

    def get_log(self, log_id: str) -> ExecutionLog | None:
        return self._execution_logs.get(log_id)
