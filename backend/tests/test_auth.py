"""
Phase 4.14 tests - Identity & RBAC Permission Layer.
Covers: User/Role CRUD, AuthService, AuthMiddleware, PermissionType,
AuthContext, API endpoints, permission resolution, audit integration.
"""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.auth.models import (
    User, Role, AuthContext, PermissionType, ROLE_PERMISSIONS,
)
from app.auth.service import AuthService, get_auth_service, reset_auth_service
from app.auth.middleware import AuthMiddleware
from app.auth.permission import (
    get_auth_context,
    check_permission,
    check_resource_access,
)
from app.runtime.manager import get_runtime, reset_runtime


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_auth_service()
    yield
    reset_runtime()
    reset_auth_service()


# =============================================================================
# Helper
# =============================================================================

async def _api(method: str, path: str, json_data=None, params=None, headers=None):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        if method == "GET":
            resp = await client.get(f"/api/v1{path}", params=params, headers=headers or {})
        elif method == "POST":
            resp = await client.post(f"/api/v1{path}", json=json_data, params=params, headers=headers or {})
        elif method == "PATCH":
            resp = await client.patch(f"/api/v1{path}", json=json_data, headers=headers or {})
        elif method == "DELETE":
            resp = await client.delete(f"/api/v1{path}", headers=headers or {})
        return resp


# =============================================================================
# User Model Tests
# =============================================================================

class TestUserModel:
    def test_create_user_minimal(self):
        user = User(id="u1", username="test", email="test@test.com")
        assert user.id == "u1"
        assert user.username == "test"
        assert user.roles == []
        assert user.is_active is True

    def test_user_to_dict(self):
        ts = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)
        user = User(
            id="u1", username="admin", email="a@b.com",
            roles=["admin"], is_active=True,
            created_at=ts, updated_at=ts,
        )
        d = user.to_dict()
        assert d["id"] == "u1"
        assert d["username"] == "admin"
        assert d["roles"] == ["admin"]
        assert d["is_active"] is True

    def test_user_to_dict_with_metadata(self):
        user = User(id="u2", username="meta", email="m@m.com", metadata={"key": "val"})
        assert user.to_dict()["metadata"] == {"key": "val"}


# =============================================================================
# Role Model Tests
# =============================================================================

class TestRoleModel:
    def test_create_role(self):
        role = Role(id="r1", name="admin", description="Admin role", permissions=["task:create"])
        assert role.id == "r1"
        assert role.name == "admin"

    def test_role_has_permission(self):
        role = Role(id="r1", name="test", description="T", permissions=["task:read", "task:create"])
        assert role.has_permission(PermissionType.TASK_READ) is True
        assert role.has_permission("task:create") is True
        assert role.has_permission(PermissionType.TASK_DELETE) is False

    def test_role_to_dict(self):
        role = Role(id="r1", name="viewer", description="V", permissions=["task:read"])
        d = role.to_dict()
        assert d["id"] == "r1"
        assert d["permissions"] == ["task:read"]


# =============================================================================
# AuthContext Tests
# =============================================================================

class TestAuthContext:
    def test_anonymous_context(self):
        ctx = AuthContext(user_id="anon", username="anon", roles=[])
        assert ctx.is_authenticated is False
        assert ctx.has_permission("anything") is False

    def test_authenticated_context(self):
        ctx = AuthContext(
            user_id="u1", username="admin", roles=["admin"],
            permissions=["task:create", "task:read"],
            is_authenticated=True,
        )
        assert ctx.has_permission("task:create") is True
        assert ctx.has_permission("task:delete") is False

    def test_has_any_permission(self):
        ctx = AuthContext(
            user_id="u1", username="op", roles=["operator"],
            permissions=["task:read", "agent:read"],
            is_authenticated=True,
        )
        assert ctx.has_any_permission(["task:read", "task:delete"]) is True
        assert ctx.has_any_permission(["task:delete", "task:create"]) is False

    def test_has_all_permissions(self):
        ctx = AuthContext(
            user_id="u1", username="admin", roles=["admin"],
            permissions=["task:read", "task:create"],
            is_authenticated=True,
        )
        assert ctx.has_all_permissions(["task:read", "task:create"]) is True
        assert ctx.has_all_permissions(["task:read", "task:delete"]) is False

    def test_to_dict(self):
        ctx = AuthContext(
            user_id="u1", username="test", roles=["admin"],
            permissions=["task:read"], is_authenticated=True,
            request_id="req-1",
        )
        d = ctx.to_dict()
        assert d["user_id"] == "u1"
        assert d["roles"] == ["admin"]
        assert d["request_id"] == "req-1"


# =============================================================================
# PermissionType Tests
# =============================================================================

class TestPermissionType:
    def test_all_permissions_have_unique_values(self):
        values = [p.value for p in PermissionType]
        assert len(values) == len(set(values))

    def test_permission_format(self):
        for p in PermissionType:
            assert ":" in p.value, f"Permission {p} should have ':' separator"

    def test_enum_to_string(self):
        assert PermissionType.TASK_CREATE.value == "task:create"
        assert PermissionType.ADMIN_SYSTEM.value == "admin:system"


# =============================================================================
# ROLE_PERMISSIONS Tests
# =============================================================================

class TestRolePermissions:
    def test_admin_has_all(self):
        assert len(ROLE_PERMISSIONS["admin"]) == len(PermissionType)

    def test_operator_has_many(self):
        perms = ROLE_PERMISSIONS["operator"]
        assert PermissionType.TASK_CREATE in perms
        assert PermissionType.AGENT_READ in perms
        assert PermissionType.ADMIN_SYSTEM not in perms

    def test_viewer_has_read_only(self):
        perms = ROLE_PERMISSIONS["viewer"]
        assert PermissionType.TASK_READ in perms
        assert PermissionType.AGENT_READ in perms
        assert PermissionType.TASK_CREATE not in perms
        assert PermissionType.TASK_DELETE not in perms

    def test_agent_has_limited(self):
        perms = ROLE_PERMISSIONS["agent"]
        assert PermissionType.TASK_READ in perms
        assert PermissionType.ARTIFACT_CREATE in perms
        assert PermissionType.TASK_DELETE not in perms


# =============================================================================
# AuthService Tests
# =============================================================================

class TestAuthServiceUsers:
    def test_create_user(self):
        svc = AuthService()
        user = svc.create_user("testuser", "test@test.com", roles=["role-viewer"])
        assert user.username == "testuser"
        assert "role-viewer" in user.roles

    def test_get_user(self):
        svc = AuthService()
        user = svc.create_user("testuser", "test@test.com")
        found = svc.get_user(user.id)
        assert found is not None
        assert found.username == "testuser"

    def test_get_user_not_found(self):
        svc = AuthService()
        assert svc.get_user("nonexistent") is None

    def test_get_user_by_username(self):
        svc = AuthService()
        svc.create_user("alice", "alice@test.com")
        user = svc.get_user_by_username("alice")
        assert user is not None
        assert user.email == "alice@test.com"

    def test_get_user_by_username_not_found(self):
        svc = AuthService()
        assert svc.get_user_by_username("nonexistent") is None

    def test_list_users(self):
        svc = AuthService()
        svc.create_user("u1", "u1@t.com")
        svc.create_user("u2", "u2@t.com")
        users = svc.list_users()
        assert len(users) >= 3  # 2 created + admin default

    def test_update_user(self):
        svc = AuthService()
        user = svc.create_user("oldname", "old@t.com")
        updated = svc.update_user(user.id, username="newname", email="new@t.com")
        assert updated.username == "newname"
        assert updated.email == "new@t.com"

    def test_update_user_not_found(self):
        svc = AuthService()
        assert svc.update_user("nonexistent", username="x") is None

    def test_delete_user(self):
        svc = AuthService()
        user = svc.create_user("todelete", "del@t.com")
        assert svc.delete_user(user.id) is True
        assert svc.get_user(user.id) is None

    def test_delete_user_not_found(self):
        svc = AuthService()
        assert svc.delete_user("nonexistent") is False

    def test_default_admin_exists(self):
        svc = AuthService()
        admin = svc.get_user_by_username("admin")
        assert admin is not None
        assert "role-admin" in admin.roles


class TestAuthServiceRoles:
    def test_list_roles(self):
        svc = AuthService()
        roles = svc.list_roles()
        assert len(roles) == 4  # admin, operator, viewer, agent

    def test_get_role(self):
        svc = AuthService()
        role = svc.get_role("role-admin")
        assert role is not None
        assert role.name == "admin"

    def test_get_role_by_name(self):
        svc = AuthService()
        role = svc.get_role_by_name("viewer")
        assert role is not None
        assert PermissionType.TASK_READ.value in role.permissions

    def test_create_custom_role(self):
        svc = AuthService()
        role = svc.create_role("custom", "Custom role", ["task:read"])
        assert role.name == "custom"
        assert "task:read" in role.permissions

    def test_update_role(self):
        svc = AuthService()
        role = svc.create_role("temp", "Temp", ["task:read"])
        updated = svc.update_role(role.id, name="renamed", permissions=["task:read", "task:create"])
        assert updated.name == "renamed"
        assert len(updated.permissions) == 2

    def test_delete_role(self):
        svc = AuthService()
        role = svc.create_role("todelete", "Del", [])
        assert svc.delete_role(role.id) is True
        assert svc.get_role(role.id) is None


class TestAuthServicePermissions:
    def test_resolve_permissions_admin(self):
        svc = AuthService()
        perms = svc.resolve_permissions(["role-admin"])
        assert len(perms) == len(PermissionType)

    def test_resolve_permissions_viewer(self):
        svc = AuthService()
        perms = svc.resolve_permissions(["role-viewer"])
        assert "task:read" in perms
        assert "task:create" not in perms

    def test_resolve_permissions_multiple_roles(self):
        svc = AuthService()
        svc.create_role("custom-read", "Custom Read", ["artifact:read"])
        perms = svc.resolve_permissions(["role-viewer", "custom-read"])
        assert "task:read" in perms
        assert "artifact:read" in perms

    def test_resolve_permissions_unknown_role(self):
        svc = AuthService()
        perms = svc.resolve_permissions(["nonexistent-role"])
        assert perms == []


class TestAuthServiceAuthContext:
    def test_get_auth_context_anonymous(self):
        svc = AuthService()
        ctx = svc.get_auth_context(user_id=None)
        assert ctx.is_authenticated is False
        assert ctx.user_id == "anonymous"

    def test_get_auth_context_authenticated(self):
        svc = AuthService()
        admin = svc.get_user_by_username("admin")
        ctx = svc.get_auth_context(user_id=admin.id)
        assert ctx.is_authenticated is True
        assert ctx.username == "admin"
        assert len(ctx.permissions) > 0

    def test_get_auth_context_inactive(self):
        svc = AuthService()
        admin = svc.get_user_by_username("admin")
        svc.update_user(admin.id, is_active=False)
        ctx = svc.get_auth_context(user_id=admin.id)
        assert ctx.is_authenticated is False

    def test_get_auth_context_with_request_id(self):
        svc = AuthService()
        ctx = svc.get_auth_context(user_id=None, request_id="req-123")
        assert ctx.request_id == "req-123"


# =============================================================================
# Permission Checking Tests
# =============================================================================

class TestPermissionChecking:
    def test_check_permission_true(self):
        ctx = AuthContext(
            user_id="u1", username="admin", roles=["admin"],
            permissions=["task:create"], is_authenticated=True,
        )
        assert check_permission(ctx, PermissionType.TASK_CREATE) is True

    def test_check_permission_false(self):
        ctx = AuthContext(
            user_id="u1", username="viewer", roles=["viewer"],
            permissions=["task:read"], is_authenticated=True,
        )
        assert check_permission(ctx, PermissionType.TASK_DELETE) is False

    def test_check_resource_access_admin(self):
        ctx = AuthContext(
            user_id="admin", username="admin", roles=["admin"],
            permissions=["admin:system"], is_authenticated=True,
        )
        assert check_resource_access(ctx, resource_owner_id="other") is True

    def test_check_resource_access_owner(self):
        ctx = AuthContext(
            user_id="u1", username="owner", roles=["viewer"],
            permissions=["task:read"], is_authenticated=True,
        )
        assert check_resource_access(ctx, resource_owner_id="u1", permission=PermissionType.TASK_READ) is True

    def test_check_resource_access_no_perm(self):
        ctx = AuthContext(
            user_id="u2", username="stranger", roles=["viewer"],
            permissions=["task:read"], is_authenticated=True,
        )
        assert check_resource_access(ctx, resource_owner_id="u1", permission=PermissionType.TASK_DELETE) is False


# =============================================================================
# Singleton Tests
# =============================================================================

class TestAuthServiceSingleton:
    def test_get_auth_service_singleton(self):
        reset_auth_service()
        svc1 = get_auth_service()
        svc2 = get_auth_service()
        assert svc1 is svc2

    def test_reset_auth_service(self):
        reset_auth_service()
        svc1 = get_auth_service()
        reset_auth_service()
        svc2 = get_auth_service()
        assert svc1 is not svc2


# =============================================================================
# API Endpoint Tests
# =============================================================================

class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_get_me_anonymous(self):
        resp = await _api("GET", "/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_authenticated"] is False

    @pytest.mark.asyncio
    async def test_get_me_authenticated(self):
        resp = await _api("GET", "/auth/me", headers={"X-User-ID": "user-admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_authenticated"] is True
        assert data["username"] == "admin"

    @pytest.mark.asyncio
    async def test_create_user(self):
        resp = await _api("POST", "/auth/users", json_data={
            "username": "newuser", "email": "new@test.com",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"

    @pytest.mark.asyncio
    async def test_list_users(self):
        resp = await _api("GET", "/auth/users")
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_user(self):
        resp = await _api("GET", "/auth/users/user-admin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        resp = await _api("GET", "/auth/users/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user(self):
        resp = await _api("PATCH", "/auth/users/user-admin", json_data={
            "email": "updated@test.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "updated@test.com"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        resp = await _api("PATCH", "/auth/users/nonexistent", json_data={"email": "x@x.com"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_user(self):
        # Create then delete
        create_resp = await _api("POST", "/auth/users", json_data={
            "username": "todelete", "email": "del@test.com",
        })
        user_id = create_resp.json()["id"]
        del_resp = await _api("DELETE", f"/auth/users/{user_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        resp = await _api("DELETE", "/auth/users/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_permissions(self):
        resp = await _api("GET", "/auth/users/user-admin/permissions")
        assert resp.status_code == 200
        data = resp.json()
        assert "permissions" in data
        assert len(data["permissions"]) > 0

    @pytest.mark.asyncio
    async def test_list_roles(self):
        resp = await _api("GET", "/auth/roles")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 4

    @pytest.mark.asyncio
    async def test_get_role(self):
        resp = await _api("GET", "/auth/roles/role-admin")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_role_not_found(self):
        resp = await _api("GET", "/auth/roles/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_role(self):
        resp = await _api("POST", "/auth/roles", json_data={
            "name": "tester", "description": "Test role", "permissions": ["task:read"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "tester"

    @pytest.mark.asyncio
    async def test_update_role(self):
        resp = await _api("PATCH", "/auth/roles/role-viewer", json_data={
            "description": "Updated viewer",
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_role(self):
        create_resp = await _api("POST", "/auth/roles", json_data={
            "name": "tmp", "description": "tmp", "permissions": [],
        })
        role_id = create_resp.json()["id"]
        del_resp = await _api("DELETE", f"/auth/roles/{role_id}")
        assert del_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_permissions(self):
        resp = await _api("GET", "/auth/permissions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["permissions"]) == len(PermissionType)

    @pytest.mark.asyncio
    async def test_check_permission_endpoint(self):
        resp = await _api("GET", "/auth/permissions/check", params={"permission": "task:read"}, headers={"X-User-ID": "user-admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_permission"] is True

    @pytest.mark.asyncio
    async def test_check_permission_endpoint_no_perm(self):
        resp = await _api("GET", "/auth/permissions/check", params={"permission": "nonexistent:perm"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_permission"] is False


# =============================================================================
# Audit + Auth Integration Tests
# =============================================================================

class TestAuditAuthIntegration:
    def test_audit_with_user_identity(self):
        svc = get_auth_service()
        runtime = get_runtime()

        user = svc.create_user("audit_test_user", "audit@test.com", roles=["role-operator"])
        runtime.audit_logger.record(
            actor=user.id,
            action="create_task",
            resource_type="task",
            resource_id="task-1",
            task_id="task-1",
        )

        records, _ = runtime.audit_logger.query(actor=user.id)
        assert len(records) >= 1
        assert records[0].actor == user.id

    def test_audit_with_full_user_context(self):
        runtime = get_runtime()
        runtime.audit_logger.record(
            actor="user-admin",
            action="task_started",
            resource_type="task",
            resource_id="task-2",
            task_id="task-2",
            metadata={"username": "admin", "roles": ["admin"]},
        )

        records, _ = runtime.audit_logger.query(actor="user-admin")
        assert len(records) >= 1
        assert records[0].metadata.get("username") == "admin"


# =============================================================================
# Middleware Tests
# =============================================================================

class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_x_user_id_header_sets_context(self):
        resp = await _api("GET", "/auth/me", headers={"X-User-ID": "user-admin"})
        data = resp.json()
        assert data["username"] == "admin"
        assert data["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_no_header_anonymous(self):
        resp = await _api("GET", "/auth/me")
        data = resp.json()
        assert data["is_authenticated"] is False
        assert data["user_id"] == "anonymous"

    @pytest.mark.asyncio
    async def test_invalid_user_id(self):
        resp = await _api("GET", "/auth/me", headers={"X-User-ID": "nonexistent-user"})
        data = resp.json()
        assert data["is_authenticated"] is False
# =============================================================================
# Extended AuthService Tests
# =============================================================================

class TestAuthServiceExtended:
    def test_create_user_with_metadata(self):
        svc = AuthService()
        user = svc.create_user("meta_user", "meta@t.com", metadata={"department": "IT", "level": 3})
        assert user.metadata == {"department": "IT", "level": 3}

    def test_create_user_default_roles_empty(self):
        svc = AuthService()
        user = svc.create_user("noroles", "nr@t.com")
        assert user.roles == []

    def test_update_user_roles(self):
        svc = AuthService()
        user = svc.create_user("rolechange", "rc@t.com")
        updated = svc.update_user(user.id, roles=["role-admin", "role-viewer"])
        assert "role-admin" in updated.roles
        assert "role-viewer" in updated.roles

    def test_update_user_is_active_false(self):
        svc = AuthService()
        user = svc.create_user("deactivate", "da@t.com")
        updated = svc.update_user(user.id, is_active=False)
        assert updated.is_active is False

    def test_update_user_is_active_true(self):
        svc = AuthService()
        user = svc.create_user("activate", "act@t.com", roles=[])
        svc.update_user(user.id, is_active=False)
        updated = svc.update_user(user.id, is_active=True)
        assert updated.is_active is True

    def test_update_user_metadata_merge(self):
        svc = AuthService()
        user = svc.create_user("metamerge", "mm@t.com", metadata={"a": 1})
        updated = svc.update_user(user.id, metadata={"b": 2})
        assert updated.metadata == {"b": 2}

    def test_resolve_permissions_empty_roles(self):
        svc = AuthService()
        perms = svc.resolve_permissions([])
        assert perms == []

    def test_resolve_permissions_mixed_valid_invalid(self):
        svc = AuthService()
        perms = svc.resolve_permissions(["role-viewer", "nonexistent-role"])
        assert "task:read" in perms
        assert "task:create" not in perms

    def test_role_has_permission_string_input(self):
        role = Role(id="r-x", name="x", description="X", permissions=["artifact:read"])
        assert role.has_permission("artifact:read") is True
        assert role.has_permission("task:read") is False

    def test_role_has_permission_enum_input(self):
        role = Role(id="r-x", name="x", description="X", permissions=["artifact:read"])
        assert role.has_permission(PermissionType.ARTIFACT_READ) is True

    def test_auth_context_has_permission_string(self):
        ctx = AuthContext(
            user_id="u1", username="test", roles=["viewer"],
            permissions=["task:read"], is_authenticated=True,
        )
        assert ctx.has_permission("task:read") is True
        assert ctx.has_permission("task:delete") is False

    def test_auth_context_has_any_permission_empty(self):
        ctx = AuthContext(
            user_id="u1", username="test", roles=[],
            permissions=[], is_authenticated=False,
        )
        assert ctx.has_any_permission(["task:read"]) is False

    def test_auth_context_has_all_permissions_empty(self):
        ctx = AuthContext(
            user_id="u1", username="test", roles=[],
            permissions=[], is_authenticated=False,
        )
        assert ctx.has_all_permissions(["task:read"]) is False

    def test_check_resource_access_no_owner_no_perm(self):
        ctx = AuthContext(
            user_id="u1", username="v", roles=["viewer"],
            permissions=["task:read"], is_authenticated=True,
        )
        assert check_resource_access(ctx, resource_owner_id=None, permission=None) is False

    def test_check_resource_access_owner_match(self):
        ctx = AuthContext(
            user_id="u1", username="owner", roles=[],
            permissions=[], is_authenticated=True,
        )
        assert check_resource_access(ctx, resource_owner_id="u1") is True

    def test_check_resource_access_owner_mismatch(self):
        ctx = AuthContext(
            user_id="u1", username="u1", roles=[],
            permissions=[], is_authenticated=True,
        )
        assert check_resource_access(ctx, resource_owner_id="u2") is False

    def test_resolve_user_info_known(self):
        svc = AuthService()
        info = svc.resolve_user_info("user-admin")
        assert info["username"] == "admin"
        assert "roles" in info

    def test_resolve_user_info_unknown(self):
        svc = AuthService()
        info = svc.resolve_user_info("nonexistent")
        assert info["username"] == "unknown"

    def test_clear_resets_state(self):
        svc = AuthService()
        svc.create_user("t1", "t1@t.com")
        assert len(svc.list_users()) > 1
        svc.clear()
        users = svc.list_users()
        assert len(users) == 1  # default admin
        assert users[0].username == "admin"


# =============================================================================
# Extended API Tests
# =============================================================================

class TestAuthAPIExtended:
    @pytest.mark.asyncio
    async def test_get_user_permissions_viewer(self):
        resp = await _api("GET", "/auth/users/user-admin/permissions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"

    @pytest.mark.asyncio
    async def test_create_user_with_roles(self):
        resp = await _api("POST", "/auth/users", json_data={
            "username": "roleuser", "email": "role@test.com",
            "roles": ["role-viewer"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "role-viewer" in data["roles"]

    @pytest.mark.asyncio
    async def test_update_user_not_found_404(self):
        resp = await _api("PATCH", "/auth/users/fake-id", json_data={"username": "x"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_roles_include_builtin(self):
        resp = await _api("GET", "/auth/roles")
        data = resp.json()
        names = [r["name"] for r in data["roles"]]
        assert "admin" in names
        assert "viewer" in names
        assert "operator" in names
        assert "agent" in names

    @pytest.mark.asyncio
    async def test_role_crud_cycle(self):
        # Create
        create_resp = await _api("POST", "/auth/roles", json_data={
            "name": "cycle_test", "description": "Cycle test", "permissions": ["task:read"],
        })
        assert create_resp.status_code == 201
        role_id = create_resp.json()["id"]

        # Get
        get_resp = await _api("GET", f"/auth/roles/{role_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "cycle_test"

        # Update
        patch_resp = await _api("PATCH", f"/auth/roles/{role_id}", json_data={"description": "Updated"})
        assert patch_resp.status_code == 200

        # Delete
        del_resp = await _api("DELETE", f"/auth/roles/{role_id}")
        assert del_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_user_crud_cycle(self):
        # Create
        create_resp = await _api("POST", "/auth/users", json_data={
            "username": "cycle_user", "email": "cycle@test.com",
        })
        assert create_resp.status_code == 201
        user_id = create_resp.json()["id"]

        # Get
        get_resp = await _api("GET", f"/auth/users/{user_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["username"] == "cycle_user"

        # Update
        patch_resp = await _api("PATCH", f"/auth/users/{user_id}", json_data={"email": "updated@test.com"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["email"] == "updated@test.com"

        # Delete
        del_resp = await _api("DELETE", f"/auth/users/{user_id}")
        assert del_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_permission_check_with_admin(self):
        resp = await _api("GET", "/auth/permissions/check", params={"permission": "admin:system"}, headers={"X-User-ID": "user-admin"})
        data = resp.json()
        assert data["has_permission"] is True

    @pytest.mark.asyncio
    async def test_auth_me_has_request_id(self):
        resp = await _api("GET", "/auth/me")
        data = resp.json()
        assert "request_id" in data
# =============================================================================
# Additional Permission & Edge Case Tests
# =============================================================================

class TestPermissionEnumExhaustive:
    def test_all_permissions_are_strings(self):
        for p in PermissionType:
            assert isinstance(p.value, str)

    def test_permissions_follow_resource_action_pattern(self):
        for p in PermissionType:
            parts = p.value.split(":")
            assert len(parts) == 2, f"{p} should be resource:action"

    def test_admin_role_covers_all_permissions(self):
        admin_perms = ROLE_PERMISSIONS["admin"]
        all_perms = set(PermissionType)
        assert admin_perms == all_perms


class TestRoleEdgeCases:
    def test_role_permissions_empty(self):
        role = Role(id="r-e", name="empty", description="No perms", permissions=[])
        assert role.has_permission("anything") is False

    def test_role_to_dict_with_defaults(self):
        role = Role(id="r-d", name="d", description="D")
        d = role.to_dict()
        assert d["permissions"] == []

    def test_role_update_preserves_id(self):
        role = Role(id="r-fixed", name="old", description="Old")
        role_id_before = role.id
        role.name = "new"
        assert role.id == role_id_before


class TestAuthServiceAdditional:
    def test_get_role_by_name_not_found(self):
        svc = AuthService()
        assert svc.get_role_by_name("nonexistent") is None

    def test_create_role_default_permissions(self):
        svc = AuthService()
        role = svc.create_role("minimal", "Minimal description")
        assert role.permissions == []

    def test_update_role_not_found(self):
        svc = AuthService()
        assert svc.update_role("nonexistent", name="x") is None

    def test_delete_role_not_found(self):
        svc = AuthService()
        assert svc.delete_role("nonexistent") is False

    def test_get_auth_context_inactive_user(self):
        svc = AuthService()
        user = svc.create_user("expired", "exp@t.com", roles=["role-viewer"])
        svc.update_user(user.id, is_active=False)
        ctx = svc.get_auth_context(user_id=user.id)
        assert ctx.is_authenticated is False


class TestAuthContextAdditional:
    def test_auth_context_default_values(self):
        ctx = AuthContext(user_id="x", username="x", roles=[])
        assert ctx.permissions == []
        assert ctx.is_authenticated is False
        assert ctx.request_id is None