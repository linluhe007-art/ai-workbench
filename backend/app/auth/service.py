"""
AuthService - central identity & RBAC manager.

Manages Users, Roles, Tenants, and provides AuthContext resolution.
Memory-based with database-ready interface design.
Phase 4.14: Identity & RBAC Permission Layer.
Phase 4.15: Tenant support, password hashing, JWT authentication.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from passlib.context import CryptContext

from app.auth.models import (
    User,
    Role,
    Tenant,
    TokenPair,
    AuthContext,
    PermissionType,
    ROLE_PERMISSIONS,
)
from app.auth.jwt import get_jwt_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


class AuthService:
    """Manages users, roles, tenants, and auth context resolution."""

    def __init__(self):
        self._users: dict[str, User] = {}
        self._roles: dict[str, Role] = {}
        self._tenants: dict[str, Tenant] = {}
        self._init_builtin_roles()
        self._init_default_tenants()
        self._init_default_users()

    def _init_builtin_roles(self) -> None:
        for role_name, perms in ROLE_PERMISSIONS.items():
            role = Role(
                id=f"role-{role_name}",
                name=role_name,
                description=f"Built-in {role_name} role",
                permissions=[p.value for p in perms],
            )
            self._roles[role.id] = role

    def _init_default_tenants(self) -> None:
        default_tenant = Tenant(
            id="tenant-default",
            name="Default",
            slug="default",
        )
        self._tenants[default_tenant.id] = default_tenant

    def _init_default_users(self) -> None:
        admin = User(
            id="user-admin",
            username="admin",
            email="admin@workbench.local",
            roles=["role-admin"],
            is_active=True,
            hashed_password=hash_password("admin"),
            tenant_ids=["tenant-default"],
        )
        self._users[admin.id] = admin

    # ── Tenant CRUD ──────────────────────────────────────────

    def create_tenant(self, name: str, slug: str = "", metadata: dict | None = None) -> Tenant:
        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            id=tenant_id,
            name=name,
            slug=slug or name.lower().replace(" ", "-"),
            metadata=metadata or {},
        )
        self._tenants[tenant_id] = tenant
        logger.info("Tenant created", tenant_id=tenant_id, name=name)
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        for tenant in self._tenants.values():
            if tenant.slug == slug:
                return tenant
        return None

    def list_tenants(self) -> list[Tenant]:
        return list(self._tenants.values())

    def update_tenant(self, tenant_id: str, name: str | None = None, is_active: bool | None = None) -> Tenant | None:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return None
        if name is not None:
            tenant.name = name
        if is_active is not None:
            tenant.is_active = is_active
        tenant.updated_at = datetime.now(timezone.utc)
        return tenant

    def delete_tenant(self, tenant_id: str) -> bool:
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            return True
        return False

    # ── Authentication ───────────────────────────────────────

    def authenticate(self, username: str, password: str) -> User | None:
        """Authenticate a user by username and password."""
        user = self.get_user_by_username(username)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def authenticate_with_tenant(
        self, username: str, password: str, tenant_id: str = "",
    ) -> tuple[User | None, Tenant | None]:
        """Authenticate and verify tenant membership."""
        user = self.authenticate(username, password)
        if user is None:
            return None, None
        if tenant_id and tenant_id not in user.tenant_ids:
            return user, None
        tenant = self._tenants.get(tenant_id) if tenant_id else None
        return user, tenant

    def login(
        self, username: str, password: str, tenant_id: str = "",
    ) -> TokenPair | None:
        """Authenticate and return a token pair."""
        user, tenant = self.authenticate_with_tenant(username, password, tenant_id)
        if user is None:
            return None

        actual_tenant_id = tenant_id or (user.tenant_ids[0] if user.tenant_ids else "tenant-default")
        jwt_mgr = get_jwt_manager()

        access_token = jwt_mgr.create_access_token(
            user_id=user.id,
            tenant_id=actual_tenant_id,
            username=user.username,
        )
        refresh_token = jwt_mgr.create_refresh_token(
            user_id=user.id,
            tenant_id=actual_tenant_id,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=jwt_mgr._access_expire_minutes * 60,
        )

    def refresh_access_token(self, refresh_token_str: str) -> TokenPair | None:
        """Use a refresh token to get a new token pair."""
        jwt_mgr = get_jwt_manager()
        payload = jwt_mgr.validate_refresh_token(refresh_token_str)
        if payload is None:
            return None

        user_id = payload.get("sub", "")
        tenant_id = payload.get("tenant_id", "")
        user = self._users.get(user_id)
        if user is None or not user.is_active:
            return None

        access_token = jwt_mgr.create_access_token(
            user_id=user_id,
            tenant_id=tenant_id,
            username=user.username,
        )
        refresh_token = jwt_mgr.create_refresh_token(
            user_id=user_id,
            tenant_id=tenant_id,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=jwt_mgr._access_expire_minutes * 60,
        )

    # ── User CRUD ────────────────────────────────────────────

    def create_user(
        self,
        username: str,
        email: str,
        password: str = "",
        roles: list[str] | None = None,
        tenant_ids: list[str] | None = None,
        metadata: dict | None = None,
    ) -> User:
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username=username,
            email=email,
            roles=roles or [],
            is_active=True,
            hashed_password=hash_password(password) if password else "",
            tenant_ids=tenant_ids or [],
            metadata=metadata or {},
        )
        self._users[user_id] = user
        logger.info("User created", user_id=user_id, username=username)
        return user

    def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> User | None:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def list_users(self, tenant_id: str = "") -> list[User]:
        users = list(self._users.values())
        if tenant_id:
            users = [u for u in users if tenant_id in u.tenant_ids]
        return users

    def update_user(
        self,
        user_id: str,
        username: str | None = None,
        email: str | None = None,
        roles: list[str] | None = None,
        is_active: bool | None = None,
        password: str | None = None,
        tenant_ids: list[str] | None = None,
        metadata: dict | None = None,
    ) -> User | None:
        user = self._users.get(user_id)
        if user is None:
            return None
        if username is not None:
            user.username = username
        if email is not None:
            user.email = email
        if roles is not None:
            user.roles = roles
        if is_active is not None:
            user.is_active = is_active
        if password is not None:
            user.hashed_password = hash_password(password)
        if tenant_ids is not None:
            user.tenant_ids = tenant_ids
        if metadata is not None:
            user.metadata = metadata
        user.updated_at = datetime.now(timezone.utc)
        return user

    def delete_user(self, user_id: str) -> bool:
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False

    # ── Role CRUD ────────────────────────────────────────────

    def create_role(self, name: str, description: str, permissions: list[str] | None = None, tenant_id: str = "") -> Role:
        role_id = str(uuid.uuid4())
        role = Role(
            id=role_id, name=name, description=description,
            permissions=permissions or [], tenant_id=tenant_id,
        )
        self._roles[role_id] = role
        return role

    def get_role(self, role_id: str) -> Role | None:
        return self._roles.get(role_id)

    def get_role_by_name(self, name: str) -> Role | None:
        for role in self._roles.values():
            if role.name == name:
                return role
        return None

    def list_roles(self, tenant_id: str = "") -> list[Role]:
        roles = list(self._roles.values())
        if tenant_id:
            roles = [r for r in roles if r.tenant_id == tenant_id or r.tenant_id == ""]
        return roles

    def update_role(self, role_id: str, name: str | None = None, description: str | None = None, permissions: list[str] | None = None) -> Role | None:
        role = self._roles.get(role_id)
        if role is None:
            return None
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if permissions is not None:
            role.permissions = permissions
        role.updated_at = datetime.now(timezone.utc)
        return role

    def delete_role(self, role_id: str) -> bool:
        if role_id in self._roles:
            del self._roles[role_id]
            return True
        return False

    # ── Permission Resolution ────────────────────────────────

    def resolve_permissions(self, role_ids: list[str]) -> list[str]:
        perms: set[str] = set()
        for role_id in role_ids:
            role = self._roles.get(role_id)
            if role:
                perms.update(role.permissions)
        return sorted(perms)

    def get_auth_context(self, user_id: str | None = None, tenant_id: str = "", request_id: str | None = None) -> AuthContext:
        if user_id is None:
            return AuthContext(
                user_id="anonymous", username="anonymous", roles=[],
                permissions=[], tenant_id=tenant_id,
                is_authenticated=False, request_id=request_id,
            )
        user = self._users.get(user_id)
        if user is None or not user.is_active:
            return AuthContext(
                user_id=user_id, username="unknown", roles=[],
                permissions=[], tenant_id=tenant_id,
                is_authenticated=False, request_id=request_id,
            )
        permissions = self.resolve_permissions(user.roles)
        return AuthContext(
            user_id=user.id, username=user.username, roles=user.roles,
            permissions=permissions, tenant_id=tenant_id or (user.tenant_ids[0] if user.tenant_ids else ""),
            is_authenticated=True, request_id=request_id,
        )

    def get_auth_context_from_token(self, token: str, request_id: str | None = None) -> AuthContext:
        jwt_mgr = get_jwt_manager()
        payload = jwt_mgr.decode_token_safe(token)
        if payload is None:
            return AuthContext(
                user_id="anonymous", username="anonymous", roles=[],
                permissions=[], is_authenticated=False, request_id=request_id,
            )
        user_id = payload.get("sub", "")
        tenant_id = payload.get("tenant_id", "")
        return self.get_auth_context(user_id=user_id, tenant_id=tenant_id, request_id=request_id)

    def resolve_user_info(self, user_id: str) -> dict:
        user = self._users.get(user_id)
        if user is None:
            return {"user_id": user_id, "username": "unknown"}
        return {"user_id": user.id, "username": user.username, "roles": user.roles}

    # ── Lifecycle ────────────────────────────────────────────

    def clear(self) -> None:
        self._users.clear()
        self._roles.clear()
        self._tenants.clear()
        self._init_builtin_roles()
        self._init_default_tenants()
        self._init_default_users()


# ── Global singleton ────────────────────────────────────────

_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def reset_auth_service() -> None:
    global _auth_service
    _auth_service = None