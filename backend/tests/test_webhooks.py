"""
Phase 4.24 tests - WebhookManager
Covers: subscribe, unsubscribe, list, tenant isolation, dispatch
"""
import pytest
from app.openapi.webhooks import WebhookManager, get_webhook_manager, reset_webhook_manager
from app.openapi.models import WebhookSubscription, WebhookEventType


@pytest.fixture(autouse=True)
def _reset():
    reset_webhook_manager()
    yield
    reset_webhook_manager()


@pytest.fixture
def manager():
    return WebhookManager()


class TestWebhookSubscription:
    def test_subscribe(self, manager):
        sub = manager.subscribe("https://example.com/hook")
        assert sub.url == "https://example.com/hook"
        assert sub.id.startswith("wh-")
        assert sub.enabled is True

    def test_subscribe_with_events(self, manager):
        sub = manager.subscribe("https://example.com/hook", events=["task.completed"])
        assert sub.events == ["task.completed"]

    def test_subscribe_with_tenant(self, manager):
        sub = manager.subscribe("https://example.com/hook", tenant_id="t1")
        assert sub.tenant_id == "t1"

    def test_subscribe_generates_secret(self, manager):
        sub = manager.subscribe("https://example.com/hook")
        assert len(sub.secret) > 0

    def test_unsubscribe(self, manager):
        sub = manager.subscribe("https://example.com/hook")
        assert manager.unsubscribe(sub.id) is True
        assert manager.get_subscription(sub.id) is None

    def test_unsubscribe_nonexistent(self, manager):
        assert manager.unsubscribe("nonexistent") is False

    def test_get_subscription(self, manager):
        sub = manager.subscribe("https://example.com/hook")
        found = manager.get_subscription(sub.id)
        assert found.id == sub.id


class TestWebhookListing:
    def test_list_all(self, manager):
        manager.subscribe("https://a.com/hook")
        manager.subscribe("https://b.com/hook")
        subs = manager.list_subscriptions()
        assert len(subs) == 2

    def test_list_by_tenant(self, manager):
        manager.subscribe("https://a.com/hook", tenant_id="t1")
        manager.subscribe("https://b.com/hook", tenant_id="t2")
        t1_subs = manager.list_subscriptions(tenant_id="t1")
        assert len(t1_subs) == 1

    def test_list_empty(self, manager):
        subs = manager.list_subscriptions()
        assert subs == []


class TestWebhookTenantIsolation:
    def test_belongs_to_tenant(self, manager):
        sub = manager.subscribe("https://example.com/hook", tenant_id="t1")
        assert manager.belongs_to_tenant(sub.id, "t1") is True
        assert manager.belongs_to_tenant(sub.id, "t2") is False

    def test_belongs_to_tenant_nonexistent(self, manager):
        assert manager.belongs_to_tenant("nonexistent", "t1") is False


class TestWebhookDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_no_subscriptions(self, manager):
        result = await manager.dispatch("task.completed", {"task_id": "t1"})
        assert result["dispatched"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_dispatch_filtered_by_event(self, manager):
        manager.subscribe("https://example.com/hook", events=["task.completed"])
        result = await manager.dispatch("artifact.created", {"task_id": "t1"})
        assert result["dispatched"] == 0

    @pytest.mark.asyncio
    async def test_dispatch_skips_disabled(self, manager):
        sub = manager.subscribe("https://example.com/hook", events=["task.completed"])
        sub.enabled = False
        result = await manager.dispatch("task.completed", {"task_id": "t1"})
        assert result["dispatched"] == 0


class TestWebhookSubscriptionModel:
    def test_to_dict(self, manager):
        sub = manager.subscribe("https://example.com/hook", events=["task.completed"])
        d = sub.to_dict()
        assert d["url"] == "https://example.com/hook"
        assert d["events"] == ["task.completed"]
        assert "secret" not in d  # secret not exposed
        assert d["enabled"] is True

    def test_delivery_counters(self, manager):
        sub = manager.subscribe("https://example.com/hook")
        assert sub.delivery_count == 0
        assert sub.failure_count == 0


class TestWebhookSingleton:
    def test_singleton(self):
        a = get_webhook_manager()
        b = get_webhook_manager()
        assert a is b

    def test_reset(self):
        a = get_webhook_manager()
        reset_webhook_manager()
        b = get_webhook_manager()
        assert a is not b

class TestWebhookEdgeCases:
    def test_subscribe_default_events(self, manager):
        sub = manager.subscribe("https://example.com/hook")
        assert len(sub.events) == len(WebhookEventType)

    def test_subscribe_empty_events(self, manager):
        sub = manager.subscribe("https://example.com/hook", events=[])
        assert sub.events == []

    def test_multiple_subs_same_url(self, manager):
        s1 = manager.subscribe("https://example.com/hook")
        s2 = manager.subscribe("https://example.com/hook")
        assert s1.id != s2.id

    def test_unsubscribe_twice(self, manager):
        sub = manager.subscribe("https://example.com/hook")
        manager.unsubscribe(sub.id)
        assert manager.unsubscribe(sub.id) is False

    def test_to_dict_no_secret_leak(self, manager):
        sub = manager.subscribe("https://example.com/hook")
        d = sub.to_dict()
        assert "secret" not in d


class TestWebhookEventType:
    def test_event_types(self):
        assert WebhookEventType.TASK_COMPLETED.value == "task.completed"
        assert WebhookEventType.TASK_FAILED.value == "task.failed"
        assert WebhookEventType.ARTIFACT_CREATED.value == "artifact.created"
        assert WebhookEventType.AGENT_FAILED.value == "agent.failed"

    def test_event_type_count(self):
        assert len(WebhookEventType) == 4


class TestWebhookDispatchMore:
    @pytest.mark.asyncio
    async def test_dispatch_tenant_filtering(self, manager):
        manager.subscribe("https://a.com/hook", events=["task.completed"], tenant_id="t1")
        result = await manager.dispatch("task.completed", {"task_id": "t1"}, tenant_id="t2")
        assert result["dispatched"] == 0

    @pytest.mark.asyncio
    async def test_dispatch_returns_results(self, manager):
        result = await manager.dispatch("task.completed", {"task_id": "t1"})
        assert "results" in result