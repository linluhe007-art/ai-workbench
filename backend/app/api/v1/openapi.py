"""
Open Platform API - Phase 4.24
API key management and webhook subscription endpoints.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.openapi.api_keys import get_api_key_manager
from app.openapi.webhooks import get_webhook_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["open-platform"])

# -- Helpers --

def _get_tenant(request: Request) -> str:
    auth_ctx = getattr(request.state, "auth_context", None)
    if auth_ctx:
        return auth_ctx.tenant_id
    return ""


# -- API Key Requests --

class CreateAPIKeyRequest(BaseModel):
    name: str
    permissions: list[str] = ["read"]


# -- API Keys --

@router.post("/api-keys")
async def create_api_key(req: CreateAPIKeyRequest, request: Request):
    """Create a new API key. The raw key is returned only once."""
    manager = get_api_key_manager()
    tenant = _get_tenant(request)
    api_key, raw_key = manager.create_key(
        name=req.name,
        tenant_id=tenant,
        permissions=req.permissions,
    )
    return {
        "api_key": api_key.to_dict(),
        "raw_key": raw_key,
    }


@router.get("/api-keys")
async def list_api_keys(request: Request):
    """List all API keys for the current tenant."""
    manager = get_api_key_manager()
    tenant = _get_tenant(request)
    keys = manager.list_keys(tenant_id=tenant)
    return {"api_keys": keys, "total": len(keys)}


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: str, request: Request):
    """Delete an API key."""
    manager = get_api_key_manager()
    key = manager.get_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    tenant = _get_tenant(request)
    if tenant and not manager.belongs_to_tenant(key_id, tenant):
        raise HTTPException(status_code=403, detail="Access denied")
    ok = manager.delete_key(key_id)
    return {"success": ok}


# -- Webhook Requests --

class CreateWebhookRequest(BaseModel):
    url: str
    events: list[str] | None = None


# -- Webhooks --

@router.post("/webhooks")
async def create_webhook(req: CreateWebhookRequest, request: Request):
    """Register a new webhook subscription."""
    manager = get_webhook_manager()
    tenant = _get_tenant(request)
    sub = manager.subscribe(
        url=req.url,
        events=req.events,
        tenant_id=tenant,
    )
    return {"webhook": sub.to_dict()}


@router.get("/webhooks")
async def list_webhooks(request: Request):
    """List all webhook subscriptions for the current tenant."""
    manager = get_webhook_manager()
    tenant = _get_tenant(request)
    subs = manager.list_subscriptions(tenant_id=tenant)
    return {"webhooks": subs, "total": len(subs)}


@router.delete("/webhooks/{subscription_id}")
async def delete_webhook(subscription_id: str, request: Request):
    """Delete a webhook subscription."""
    manager = get_webhook_manager()
    sub = manager.get_subscription(subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook not found")
    tenant = _get_tenant(request)
    if tenant and not manager.belongs_to_tenant(subscription_id, tenant):
        raise HTTPException(status_code=403, detail="Access denied")
    ok = manager.unsubscribe(subscription_id)
    return {"success": ok}