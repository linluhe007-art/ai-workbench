"""
Auth data models: User, Role, Permission, Tenant, RBAC types.

Memory-based implementation designed with database-ready interfaces.
Phase 4.14: Identity & RBAC Permission Layer.
Phase 4.15: Tenant model, password hashing, JWT support.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PermissionType(str, Enum):
    """Granular permission types aligned with resource types."""
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_CONTROL = "task:control"
    AGENT_READ = "agent:read"
    AGENT_MANAGE = "agent:manage"
    ARTIFACT_READ = "artifact:read"
    ARTIFACT_CREATE = "artifact:create"
    ARTIFACT_DELETE = "artifact:delete"
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_MANAGE = "workspace:manage"
    AUDIT_READ = "audit:read"
    ADMIN_MANAGE_USERS = "admin:manage_users"
    ADMIN_MANAGE_ROLES = "admin:manage_roles"
    ADMIN_SYSTEM = "admin:system"


ROLE_PERMISSIONS: dict[str, set[PermissionType]] = {
    "admin": set(PermissionType),
    "operator": {
        PermissionType.TASK_CREATE, PermissionType.TASK_READ, PermissionType.TASK_UPDATE,
        PermissionType.TASK_CONTROL, PermissionType.TASK_DELETE,
        PermissionType.AGENT_READ, PermissionType.AGENT_MANAGE,
        PermissionType.ARTIFACT_READ, PermissionType.ARTIFACT_CREATE, PermissionType.ARTIFACT_DELETE,
        PermissionType.WORKSPACE_READ, PermissionType.WORKSPACE_MANAGE,
        PermissionType.AUDIT_READ,
    },
    "viewer": {
        PermissionType.TASK_READ, PermissionType.AGENT_READ,
        PermissionType.ARTIFACT_READ, PermissionType.WORKSPACE_READ,
        PermissionType.AUDIT_READ,
    },
    "agent": {
        PermissionType.TASK_READ, PermissionType.AGENT_READ,
        PermissionType.ARTIFACT_CREATE, PermissionType.ARTIFACT_READ,
        PermissionType.WORKSPACE_READ,
    },
}


@dataclass
class Tenant:
    """A multi-tenant organization/workspace boundary."""
    id: str
    name: str
    slug: str
    is_active: bool = True
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Role:
    """A named role with associated permissions."""
    id: str
    name: str
    description: str
    permissions: list[str] = field(default_factory=list)
    tenant_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def has_permission(self, permission: PermissionType | str) -> bool:
        perm_str = permission.value if isinstance(permission, PermissionType) else permission
        return perm_str in self.permissions

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class User:
    """A user with roles, password, and tenant membership."""
    id: str
    username: str
    email: str
    roles: list[str] = field(default_factory=list)
    is_active: bool = True
    hashed_password: str = ""
    tenant_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "is_active": self.is_active,
            "hashed_password": "********" if self.hashed_password else "",
            "tenant_ids": self.tenant_ids,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class TokenPair:
    """Access + refresh token pair returned on login/refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


@dataclass
class AuthContext:
    """Represents the authenticated context for a request."""
    user_id: str
    username: str
    roles: list[str]
    permissions: list[str] = field(default_factory=list)
    tenant_id: str = ""
    is_authenticated: bool = False
    request_id: str | None = None

    def has_permission(self, permission: PermissionType | str) -> bool:
        perm_str = permission.value if isinstance(permission, PermissionType) else permission
        return perm_str in self.permissions

    def has_any_permission(self, permissions: list[PermissionType | str]) -> bool:
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, permissions: list[PermissionType | str]) -> bool:
        return all(self.has_permission(p) for p in permissions)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "roles": self.roles,
            "permissions": self.permissions,
            "tenant_id": self.tenant_id,
            "is_authenticated": self.is_authenticated,
            "request_id": self.request_id,
        }