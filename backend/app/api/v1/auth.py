"""
Auth API - user, role, permission, tenant, and JWT auth endpoints.
Phase 4.14: Identity & RBAC Permission Layer.
Phase 4.15: JWT login/refresh, tenant management.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.service import get_auth_service
from app.auth.permission import get_auth_context
from app.auth.models import PermissionType
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request Models ──────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    tenant_id: str = Field(default="")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., max_length=100)
    password: str = Field(default="")
    roles: list[str] = Field(default_factory=list)
    tenant_ids: list[str] = Field(default_factory=list)
    metadata: dict | None = None


class UserUpdateRequest(BaseModel):
    username: str | None = Field(None, min_length=1, max_length=50)
    email: str | None = Field(None, max_length=100)
    password: str | None = None
    roles: list[str] | None = None
    is_active: bool | None = None
    tenant_ids: list[str] | None = None
    metadata: dict | None = None


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., max_length=200)
    permissions: list[str] = Field(default_factory=list)
    tenant_id: str = Field(default="")


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=200)
    permissions: list[str] | None = None


class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(default="")
    metadata: dict | None = None


# ── Authentication Endpoints ────────────────────────────────

@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate user and return JWT token pair."""
    svc = get_auth_service()
    result = svc.login(req.username, req.password, req.tenant_id)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "token_type": result.token_type,
        "expires_in": result.expires_in,
    }


@router.post("/refresh")
async def refresh_token(req: RefreshRequest):
    """Exchange a refresh token for a new token pair."""
    svc = get_auth_service()
    result = svc.refresh_access_token(req.refresh_token)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    return {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "token_type": result.token_type,
        "expires_in": result.expires_in,
    }


@router.post("/logout")
async def logout(request: Request):
    """Logout (client-side token invalidation)."""
    ctx = get_auth_context(request)
    logger.info("User logged out", user_id=ctx.user_id)
    return {"success": True, "message": "Logged out"}


# ── Auth Context ────────────────────────────────────────────

@router.get("/me")
async def get_current_user(request: Request):
    ctx = get_auth_context(request)
    return ctx.to_dict()


# ── Tenant Endpoints ────────────────────────────────────────

@router.post("/tenants", status_code=201)
async def create_tenant(req: TenantCreateRequest):
    svc = get_auth_service()
    tenant = svc.create_tenant(name=req.name, slug=req.slug, metadata=req.metadata)
    return tenant.to_dict()


@router.get("/tenants")
async def list_tenants():
    svc = get_auth_service()
    tenants = svc.list_tenants()
    return {"tenants": [t.to_dict() for t in tenants], "total": len(tenants)}


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    svc = get_auth_service()
    tenant = svc.get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant.to_dict()


# ── User Endpoints ──────────────────────────────────────────

@router.post("/users", status_code=201)
async def create_user(req: UserCreateRequest):
    svc = get_auth_service()
    user = svc.create_user(
        username=req.username, email=req.email, password=req.password,
        roles=req.roles, tenant_ids=req.tenant_ids, metadata=req.metadata,
    )
    return user.to_dict()


@router.get("/users")
async def list_users(tenant_id: str = ""):
    svc = get_auth_service()
    users = svc.list_users(tenant_id=tenant_id)
    return {"users": [u.to_dict() for u in users], "total": len(users)}


@router.get("/users/{user_id}")
async def get_user(user_id: str):
    svc = get_auth_service()
    user = svc.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


@router.patch("/users/{user_id}")
async def update_user(user_id: str, req: UserUpdateRequest):
    svc = get_auth_service()
    user = svc.update_user(
        user_id=user_id, username=req.username, email=req.email,
        password=req.password, roles=req.roles, is_active=req.is_active,
        tenant_ids=req.tenant_ids, metadata=req.metadata,
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    svc = get_auth_service()
    if not svc.delete_user(user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True, "user_id": user_id}


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: str):
    svc = get_auth_service()
    user = svc.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    permissions = svc.resolve_permissions(user.roles)
    return {"user_id": user_id, "username": user.username, "roles": user.roles, "permissions": permissions}


# ── Role Endpoints ──────────────────────────────────────────

@router.post("/roles", status_code=201)
async def create_role(req: RoleCreateRequest):
    svc = get_auth_service()
    role = svc.create_role(name=req.name, description=req.description, permissions=req.permissions, tenant_id=req.tenant_id)
    return role.to_dict()


@router.get("/roles")
async def list_roles(tenant_id: str = ""):
    svc = get_auth_service()
    roles = svc.list_roles(tenant_id=tenant_id)
    return {"roles": [r.to_dict() for r in roles], "total": len(roles)}


@router.get("/roles/{role_id}")
async def get_role(role_id: str):
    svc = get_auth_service()
    role = svc.get_role(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role.to_dict()


@router.patch("/roles/{role_id}")
async def update_role(role_id: str, req: RoleUpdateRequest):
    svc = get_auth_service()
    role = svc.update_role(role_id=role_id, name=req.name, description=req.description, permissions=req.permissions)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role.to_dict()


@router.delete("/roles/{role_id}")
async def delete_role(role_id: str):
    svc = get_auth_service()
    if not svc.delete_role(role_id):
        raise HTTPException(status_code=404, detail="Role not found")
    return {"deleted": True, "role_id": role_id}


# ── Permission Endpoints ────────────────────────────────────

@router.get("/permissions")
async def list_all_permissions():
    return {"permissions": [{"key": p.value, "name": p.name} for p in PermissionType]}


@router.get("/permissions/check")
async def check_permission_endpoint(request: Request, permission: str):
    ctx = get_auth_context(request)
    has_perm = ctx.has_permission(permission)
    return {"permission": permission, "has_permission": has_perm, "user_id": ctx.user_id, "is_authenticated": ctx.is_authenticated}