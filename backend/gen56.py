import os

# Backend tests
path = r"E:\半自动工作台\backend\tests\test_automation.py"
with open(path, "w", encoding="utf-8") as f:
    f.write('''"""Phase 5.6 tests - Automation Engine"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.automation.trigger import Trigger, TriggerType, cron_matches, parse_cron
from app.automation.executor import AutomationExecutor, ExecutionLog
from app.automation.scheduler import AutomationScheduler, AutomationRule, AutomationStatus
from app.main import app


class TestTriggerType:
    def test_types(self):
        assert TriggerType.SCHEDULE == "schedule"
        assert TriggerType.EVENT == "event"
        assert TriggerType.MANUAL == "manual"
        assert TriggerType.WEBHOOK == "webhook"

    def test_schedule_factory(self):
        t = Trigger.schedule("0 18 * * *")
        assert t.trigger_type == TriggerType.SCHEDULE
        assert t.cron_expression == "0 18 * * *"

    def test_event_factory(self):
        t = Trigger.on_event("task_completed")
        assert t.trigger_type == TriggerType.EVENT
        assert t.event_name == "task_completed"

    def test_manual_factory(self):
        t = Trigger.manual()
        assert t.trigger_type == TriggerType.MANUAL

    def test_trigger_to_dict(self):
        t = Trigger.schedule("*/5 * * * *")
        d = t.to_dict()
        assert d["trigger_type"] == "schedule"
        assert d["cron_expression"] == "*/5 * * * *"


class TestCronParsing:
    def test_parse_valid(self):
        r = parse_cron("0 18 * * *")
        assert "error" not in r
        assert r["hour"] == "18"

    def test_parse_invalid(self):
        r = parse_cron("0 18")
        assert "error" in r

    def test_cron_matches_every_hour(self):
        dt = datetime(2026, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
        assert cron_matches("0 18 * * *", dt) is True
        assert cron_matches("0 19 * * *", dt) is False

    def test_cron_matches_wildcard(self):
        dt = datetime(2026, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        assert cron_matches("* * * * *", dt) is True

    def test_cron_matches_every_5_min(self):
        dt = datetime(2026, 1, 1, 12, 15, 0, tzinfo=timezone.utc)
        assert cron_matches("*/5 * * * *", dt) is True
        dt2 = datetime(2026, 1, 1, 12, 17, 0, tzinfo=timezone.utc)
        assert cron_matches("*/5 * * * *", dt2) is False

    def test_cron_matches_range(self):
        dt = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        assert cron_matches("0 9-17 * * *", dt) is True


class TestAutomationExecutor:
    async def test_execute_creates_log(self):
        executor = AutomationExecutor()
        log = await executor.execute({"id": "a1", "name": "test", "description": "test task"})
        assert log.status == "completed"
        assert log.automation_id == "a1"

    async def test_execute_with_handler(self):
        call_count = 0
        async def handler(automation):
            nonlocal call_count
            call_count += 1
            return {"handled": True}

        executor = AutomationExecutor()
        executor.register_handler("custom", handler)
        await executor.execute({"id": "a2", "name": "test", "action": {"type": "custom"}})
        assert call_count == 1

    def test_get_logs(self):
        executor = AutomationExecutor()

    def test_get_log_nonexistent(self):
        executor = AutomationExecutor()
        assert executor.get_log("nonexistent") is None


class TestAutomationScheduler:
    def test_add_rule(self):
        scheduler = AutomationScheduler()
        rule = scheduler.add_rule("test", Trigger.manual(), {"type": "test"})
        assert rule.name == "test"
        assert len(scheduler.list_rules()) == 1

    def test_remove_rule(self):
        scheduler = AutomationScheduler()
        rule = scheduler.add_rule("x", Trigger.manual(), {})
        assert scheduler.remove_rule(rule.id) is True
        assert scheduler.remove_rule("nonexistent") is False

    def test_get_rule(self):
        scheduler = AutomationScheduler()
        rule = scheduler.add_rule("test", Trigger.manual(), {})
        assert scheduler.get_rule(rule.id) is not None

    def test_list_rules(self):
        scheduler = AutomationScheduler()
        scheduler.add_rule("a", Trigger.manual(), {})
        scheduler.add_rule("b", Trigger.manual(), {})
        assert len(scheduler.list_rules()) == 2

    def test_update_status(self):
        scheduler = AutomationScheduler()
        rule = scheduler.add_rule("test", Trigger.manual(), {})
        assert scheduler.update_status(rule.id, "paused") is True
        assert scheduler.get_rule(rule.id).status == AutomationStatus.PAUSED

    def test_update_status_invalid(self):
        scheduler = AutomationScheduler()
        assert scheduler.update_status("nonexistent", "active") is False

    def test_automation_status_enum(self):
        assert AutomationStatus.ACTIVE == "active"
        assert AutomationStatus.PAUSED == "paused"
        assert AutomationStatus.DISABLED == "disabled"


class TestAutomationRule:
    def test_rule_defaults(self):
        rule = AutomationRule(name="test")
        assert rule.name == "test"
        assert rule.status == AutomationStatus.ACTIVE
        assert rule.run_count == 0

    def test_rule_to_dict(self):
        rule = AutomationRule(name="test", description="desc")
        d = rule.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "desc"
        assert "trigger" in d
        assert "action" in d


class TestAutomationAPI:
    def _client(self):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async def test_create_automation(self):
        async with self._client() as c:
            resp = await c.post("/api/v1/automation", json={"name": "test auto", "trigger_type": "manual"})
        data = resp.json()
        assert data["success"] is True
        assert data["automation"]["name"] == "test auto"

    async def test_list_automations(self):
        async with self._client() as c:
            resp = await c.get("/api/v1/automation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    async def test_get_automation(self):
        async with self._client() as c:
            create = await c.post("/api/v1/automation", json={"name": "g", "trigger_type": "manual"})
            aid = create.json()["automation"]["id"]
            resp = await c.get(f"/api/v1/automation/{aid}")
        assert resp.json()["success"] is True

    async def test_run_automation(self):
        async with self._client() as c:
            create = await c.post("/api/v1/automation", json={"name": "r", "trigger_type": "manual", "description": "run"})
            aid = create.json()["automation"]["id"]
            resp = await c.post(f"/api/v1/automation/{aid}/run")
        data = resp.json()
        assert data["success"] is True
        assert data["log"] is not None

    async def test_update_status(self):
        async with self._client() as c:
            create = await c.post("/api/v1/automation", json={"name": "s", "trigger_type": "manual"})
            aid = create.json()["automation"]["id"]
            resp = await c.put(f"/api/v1/automation/{aid}/status?status=paused")
        assert resp.json()["success"] is True

    async def test_delete_automation(self):
        async with self._client() as c:
            create = await c.post("/api/v1/automation", json={"name": "d", "trigger_type": "manual"})
            aid = create.json()["automation"]["id"]
            resp = await c.delete(f"/api/v1/automation/{aid}")
        assert resp.json()["success"] is True

    async def test_get_logs(self):
        async with self._client() as c:
            create = await c.post("/api/v1/automation", json={"name": "l", "trigger_type": "manual", "description": "log"})
            aid = create.json()["automation"]["id"]
            await c.post(f"/api/v1/automation/{aid}/run")
            resp = await c.get(f"/api/v1/automation/{aid}/logs")
        data = resp.json()
        assert data["success"] is True

    async def test_get_nonexistent(self):
        async with self._client() as c:
            resp = await c.get("/api/v1/automation/nonexistent")
        assert resp.json()["success"] is False

    async def test_create_with_schedule(self):
        async with self._client() as c:
            resp = await c.post("/api/v1/automation", json={"name": "sched", "trigger_type": "schedule", "cron_expression": "0 18 * * *"})
        data = resp.json()
        assert data["success"] is True
''')
print("Tests created")