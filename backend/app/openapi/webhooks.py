"""
WebhookManager - webhook subscription management and event dispatch.
Phase 4.24: Register webhooks, dispatch events to external URLs.
"""
import asyncio
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

import httpx

from app.openapi.models import WebhookSubscription, WebhookEventType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WebhookManager:
    """
    Manages webhook subscriptions and dispatches events.

    Features:
    - Register/deregister webhook URLs
    - Event-type filtering
    - HMAC-SHA256 request signing
    - Delivery tracking (count, failures)
    - Tenant isolation
    """

    def __init__(self):
        self._subscriptions: dict[str, WebhookSubscription] = {}

    # -- Subscription Management --

    def subscribe(
        self,
        url: str,
        events: list[str] | None = None,
        tenant_id: str = "",
    ) -> WebhookSubscription:
        """Register a new webhook subscription."""
        sub = WebhookSubscription(
            url=url,
            events=events or [e.value for e in WebhookEventType],
            secret=secrets.token_hex(16),
            tenant_id=tenant_id,
        )
        self._subscriptions[sub.id] = sub
        logger.info("Webhook subscribed", id=sub.id, url=url, events=sub.events)
        return sub

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a webhook subscription."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.info("Webhook unsubscribed", id=subscription_id)
            return True
        return False

    def get_subscription(self, subscription_id: str) -> WebhookSubscription | None:
        return self._subscriptions.get(subscription_id)

    def list_subscriptions(self, tenant_id: str = "") -> list[dict]:
        """List subscriptions, optionally filtered by tenant."""
        results = []
        for sub in self._subscriptions.values():
            if tenant_id and sub.tenant_id != tenant_id:
                continue
            results.append(sub.to_dict())
        return results

    # -- Event Dispatch --

    async def dispatch(
        self,
        event_type: str,
        payload: dict,
        tenant_id: str = "",
    ) -> dict:
        """
        Dispatch an event to all matching webhook subscriptions.

        Returns:
            {"dispatched": int, "failed": int, "results": [...]}
        """
        targets = [
            sub for sub in self._subscriptions.values()
            if sub.enabled and event_type in sub.events
            and (not tenant_id or sub.tenant_id == tenant_id)
        ]

        if not targets:
            return {"dispatched": 0, "failed": 0, "results": []}

        results = []
        dispatched = 0
        failed = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = []
            for sub in targets:
                tasks.append(self._deliver(client, sub, event_type, payload))

            delivery_results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(delivery_results):
            if isinstance(result, Exception):
                failed += 1
                targets[i].failure_count += 1
                results.append({"subscription_id": targets[i].id, "success": False, "error": str(result)})
            else:
                dispatched += 1
                targets[i].delivery_count += 1
                targets[i].last_delivery_at = datetime.now(timezone.utc)
                results.append({"subscription_id": targets[i].id, "success": True, "status": result})

        return {"dispatched": dispatched, "failed": failed, "results": results}

    async def _deliver(
        self,
        client: httpx.AsyncClient,
        sub: WebhookSubscription,
        event_type: str,
        payload: dict,
    ) -> int:
        """Deliver a single webhook event with HMAC signing."""
        body = json.dumps({
            "event": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        signature = hmac.new(
            sub.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event_type,
            "X-Webhook-ID": sub.id,
        }

        response = await client.post(sub.url, content=body, headers=headers)
        response.raise_for_status()
        return response.status_code

    # -- Tenant check --

    def belongs_to_tenant(self, subscription_id: str, tenant_id: str) -> bool:
        sub = self._subscriptions.get(subscription_id)
        return sub is not None and sub.tenant_id == tenant_id


# Singletons

_webhook_manager: WebhookManager | None = None


def get_webhook_manager() -> WebhookManager:
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager


def reset_webhook_manager() -> None:
    global _webhook_manager
    _webhook_manager = None