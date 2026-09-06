"""Automation Scheduler - Phase 5.6"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.automation.trigger import Trigger, TriggerType, cron_matches
from app.automation.executor import AutomationExecutor, ExecutionLog
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutomationStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    COMPLETED = "completed"


@dataclass
class AutomationRule:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    trigger: Trigger = field(default_factory=Trigger)
    action: dict = field(default_factory=dict)
    status: AutomationStatus = AutomationStatus.ACTIVE
    max_iterations: int = 3
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_run_at: str = ""
    run_count: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "trigger": self.trigger.to_dict(), "action": self.action,
            "status": self.status.value, "last_run_at": self.last_run_at,
            "run_count": self.run_count, "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class AutomationScheduler:
    def __init__(self, executor: AutomationExecutor | None = None):
        self._rules: dict[str, AutomationRule] = {}
        self._executor = executor or AutomationExecutor()
        self._running = False
        self._task: asyncio.Task | None = None

    def add_rule(self, name: str, trigger: Trigger, action: dict, description: str = "") -> AutomationRule:
        rule = AutomationRule(name=name, description=description, trigger=trigger, action=action)
        self._rules[rule.id] = rule
        logger.info("Automation rule added", id=rule.id, name=name)
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def get_rule(self, rule_id: str) -> AutomationRule | None:
        return self._rules.get(rule_id)

    def list_rules(self) -> list[dict]:
        return [r.to_dict() for r in self._rules.values()]

    def update_status(self, rule_id: str, status: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule:
            try:
                rule.status = AutomationStatus(status)
                rule.updated_at = datetime.now(timezone.utc).isoformat()
                return True
            except ValueError:
                return False
        return False

    async def run_rule(self, rule_id: str):
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        log = await self._executor.execute(rule.to_dict())
        rule.last_run_at = datetime.now(timezone.utc).isoformat()
        rule.run_count += 1
        return log

    async def _schedule_loop(self, interval_seconds: float = 10.0):
        while self._running:
            try:
                now = datetime.now(timezone.utc)
                for rule in list(self._rules.values()):
                    if rule.status != AutomationStatus.ACTIVE:
                        continue
                    if rule.trigger.trigger_type == TriggerType.SCHEDULE and rule.trigger.cron_expression:
                        if cron_matches(rule.trigger.cron_expression, now):
                            # Avoid duplicate runs in the same minute
                            if rule.last_run_at:
                                last = datetime.fromisoformat(rule.last_run_at.replace("Z", "+00:00"))
                                if (now - last).total_seconds() < 60:
                                    continue
                            await self.run_rule(rule.id)
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Schedule loop error", error=str(e))
                await asyncio.sleep(interval_seconds)

    def start(self, interval_seconds: float = 10.0):
        if self._running:
            return
        self._running = True
        self._task = asyncio.ensure_future(self._schedule_loop(interval_seconds))
        logger.info("Automation scheduler started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Automation scheduler stopped")

    def get_executor(self) -> AutomationExecutor:
        return self._executor
