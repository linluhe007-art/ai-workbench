"""
Phase 4.15 tests - JWT, Tenant, Password, Login/Refresh flows.
Covers: JWTManager, Tenant CRUD, password hashing, login/refresh/logout,
AuthMiddleware with Bearer token, API endpoints, tenant isolation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.auth.models import User, Role, Tenant, AuthContext, PermissionType, TokenPair
from app.auth.jwt import JWTManager, get_jwt_manager, reset_jwt_manager
from app.auth.service import (
    AuthService, get_auth_service, reset_auth_service,
    hash_password, verify_password,
)
from app.runtime.manager import get_runtime, reset_runtime


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_auth_service()
    reset_jwt_manager()
    yield
    reset_runtime()
    reset_auth_service()
    reset_jwt_manager()


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


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Password Hashing Tests
# =============================================================================

class TestPasswordHashing:
    def test_hash_password_returns_string(self):
        h = hash_password("test123")
        assert isinstance(h, str)
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_verify_correct_password(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True

    def test_verify_empty_password(self):
        h = hash_password("")
        assert verify_password("", h) is True


# =============================================================================
# JWTManager Tests
# =============================================================================

class TestJWTManager:
    def test_create_access_token(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("user-1", "tenant-1", "admin")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        mgr = get_jwt_manager()
        token = mgr.create_refresh_token("user-1", "tenant-1")
        assert isinstance(token, str)

    def test_decode_access_token(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("user-1", "tenant-1", "admin")
        payload = mgr.decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["tenant_id"] == "tenant-1"
        assert payload["username"] == "admin"
        assert payload["type"] == "access"

    def test_decode_refresh_token(self):
        mgr = get_jwt_manager()
        token = mgr.create_refresh_token("user-1", "tenant-1")
        payload = mgr.decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"

    def test_validate_access_token_passes(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("u1")
        payload = mgr.validate_access_token(token)
        assert payload is not None
        assert payload["sub"] == "u1"

    def test_validate_access_token_rejects_refresh(self):
        mgr = get_jwt_manager()
        token = mgr.create_refresh_token("u1")
        payload = mgr.validate_access_token(token)
        assert payload is None

    def test_validate_refresh_token_passes(self):
        mgr = get_jwt_manager()
        token = mgr.create_refresh_token("u1")
        payload = mgr.validate_refresh_token(token)
        assert payload is not None

    def test_validate_refresh_token_rejects_access(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("u1")
        payload = mgr.validate_refresh_token(token)
        assert payload is None

    def test_decode_invalid_token_returns_none(self):
        mgr = get_jwt_manager()
        payload = mgr.decode_token_safe("invalid.token.here")
        assert payload is None

    def test_is_token_expired_valid(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("u1")
        assert mgr.is_token_expired(token) is False

    def test_is_token_expired_invalid(self):
        mgr = get_jwt_manager()
        assert mgr.is_token_expired("garbage") is True

    def test_token_contains_iat_and_exp(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("u1")
        payload = mgr.decode_token(token)
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_singleton(self):
        reset_jwt_manager()
        m1 = get_jwt_manager()
        m2 = get_jwt_manager()
        assert m1 is m2

    def test_extra_claims(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("u1", extra_claims={"role": "admin", "scope": "full"})
        payload = mgr.decode_token(token)
        assert payload["role"] == "admin"
        assert payload["scope"] == "full"


# =============================================================================
# Tenant Model Tests
# =============================================================================

class TestTenantModel:
    def test_create_tenant(self):
        t = Tenant(id="t1", name="Org1", slug="org1")
        assert t.id == "t1"
        assert t.name == "Org1"
        assert t.is_active is True

    def test_tenant_to_dict(self):
        ts = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)
        t = Tenant(id="t1", name="Org", slug="org", created_at=ts, updated_at=ts)
        d = t.to_dict()
        assert d["id"] == "t1"
        assert d["name"] == "Org"


# =============================================================================
# TokenPair Model Tests
# =============================================================================

class TestTokenPair:
    def test_token_pair(self):
        tp = TokenPair(access_token="at", refresh_token="rt", expires_in=900)
        assert tp.access_token == "at"
        assert tp.refresh_token == "rt"
        assert tp.token_type == "bearer"
        assert tp.expires_in == 900


# =============================================================================
# AuthService: Tenant CRUD
# =============================================================================

class TestAuthServiceTenants:
    def test_create_tenant(self):
        svc = AuthService()
        t = svc.create_tenant("MyOrg", "my-org")
        assert t.name == "MyOrg"
        assert t.slug == "my-org"

    def test_default_tenant_exists(self):
        svc = AuthService()
        t = svc.get_tenant("tenant-default")
        assert t is not None
        assert t.slug == "default"

    def test_get_tenant_by_slug(self):
        svc = AuthService()
        svc.create_tenant("SlugTest", "slug-test")
        t = svc.get_tenant_by_slug("slug-test")
        assert t is not None
        assert t.name == "SlugTest"

    def test_list_tenants(self):
        svc = AuthService()
        tenants = svc.list_tenants()
        assert len(tenants) >= 1

    def test_update_tenant(self):
        svc = AuthService()
        t = svc.create_tenant("UpdateMe", "update-me")
        updated = svc.update_tenant(t.id, name="Updated")
        assert updated.name == "Updated"

    def test_delete_tenant(self):
        svc = AuthService()
        t = svc.create_tenant("Temp", "temp")
        assert svc.delete_tenant(t.id) is True
        assert svc.get_tenant(t.id) is None


# =============================================================================
# AuthService: Authentication
# =============================================================================

class TestAuthServiceAuthentication:
    def test_authenticate_success(self):
        svc = AuthService()
        user = svc.authenticate("admin", "admin")
        assert user is not None
        assert user.username == "admin"

    def test_authenticate_wrong_password(self):
        svc = AuthService()
        user = svc.authenticate("admin", "wrong")
        assert user is None

    def test_authenticate_nonexistent_user(self):
        svc = AuthService()
        user = svc.authenticate("nonexistent", "pass")
        assert user is None

    def test_authenticate_inactive_user(self):
        svc = AuthService()
        admin = svc.get_user_by_username("admin")
        svc.update_user(admin.id, is_active=False)
        user = svc.authenticate("admin", "admin")
        assert user is None

    def test_authenticate_with_tenant_success(self):
        svc = AuthService()
        user, tenant = svc.authenticate_with_tenant("admin", "admin", "tenant-default")
        assert user is not None
        assert tenant is not None
        assert tenant.slug == "default"

    def test_authenticate_with_tenant_wrong_tenant(self):
        svc = AuthService()
        user, tenant = svc.authenticate_with_tenant("admin", "admin", "other-tenant")
        assert user is not None
        assert tenant is None

    def test_login_returns_token_pair(self):
        svc = AuthService()
        result = svc.login("admin", "admin")
        assert result is not None
        assert len(result.access_token) > 0
        assert len(result.refresh_token) > 0
        assert result.token_type == "bearer"

    def test_login_wrong_password_returns_none(self):
        svc = AuthService()
        result = svc.login("admin", "wrong")
        assert result is None

    def test_refresh_access_token(self):
        svc = AuthService()
        pair = svc.login("admin", "admin")
        new_pair = svc.refresh_access_token(pair.refresh_token)
        assert new_pair is not None
        assert new_pair.access_token != pair.access_token

    def test_refresh_with_invalid_token(self):
        svc = AuthService()
        result = svc.refresh_access_token("invalid-refresh-token")
        assert result is None

    def test_refresh_with_access_token_fails(self):
        svc = AuthService()
        pair = svc.login("admin", "admin")
        result = svc.refresh_access_token(pair.access_token)
        assert result is None

    def test_refresh_with_inactive_user(self):
        svc = AuthService()
        pair = svc.login("admin", "admin")
        admin = svc.get_user_by_username("admin")
        svc.update_user(admin.id, is_active=False)
        result = svc.refresh_access_token(pair.refresh_token)
        assert result is None


# =============================================================================
# AuthService: User with Password & Tenant
# =============================================================================

class TestAuthServiceUserPassword:
    def test_create_user_with_password(self):
        svc = AuthService()
        user = svc.create_user("pwduser", "pwd@t.com", password="secret123")
        assert user.hashed_password != "secret123"
        assert verify_password("secret123", user.hashed_password)

    def test_create_user_with_tenants(self):
        svc = AuthService()
        user = svc.create_user("tuser", "t@t.com", tenant_ids=["tenant-default"])
        assert "tenant-default" in user.tenant_ids

    def test_update_user_password(self):
        svc = AuthService()
        user = svc.create_user("changepwd", "cp@t.com", password="old")
        updated = svc.update_user(user.id, password="new")
        assert verify_password("new", updated.hashed_password)

    def test_list_users_filtered_by_tenant(self):
        svc = AuthService()
        t = svc.create_tenant("FilterOrg", "filter-org")
        svc.create_user("filtered", "f@t.com", tenant_ids=[t.id])
        users = svc.list_users(tenant_id=t.id)
        assert len(users) >= 1
        usernames = [u.username for u in users]
        assert "filtered" in usernames

    def test_user_to_dict_masks_password(self):
        svc = AuthService()
        user = svc.create_user("mask", "m@t.com", password="secret")
        d = user.to_dict()
        assert d["hashed_password"] == "********"


# =============================================================================
# AuthService: AuthContext from JWT
# =============================================================================

class TestAuthContextFromToken:
    def test_get_auth_context_from_valid_token(self):
        svc = get_auth_service()
        pair = svc.login("admin", "admin")
        ctx = svc.get_auth_context_from_token(pair.access_token)
        assert ctx.is_authenticated is True
        assert ctx.username == "admin"
        assert ctx.tenant_id == "tenant-default"

    def test_get_auth_context_from_invalid_token(self):
        svc = get_auth_service()
        ctx = svc.get_auth_context_from_token("bad.token.here")
        assert ctx.is_authenticated is False

    def test_get_auth_context_from_refresh_token(self):
        svc = get_auth_service()
        pair = svc.login("admin", "admin")
        ctx = svc.get_auth_context_from_token(pair.refresh_token)
        assert ctx.is_authenticated is True


# =============================================================================
# API: Login / Refresh / Logout
# =============================================================================

class TestAuthAPILogin:
    @pytest.mark.asyncio
    async def test_login_success(self):
        resp = await _api("POST", "/auth/login", json_data={"username": "admin", "password": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        resp = await _api("POST", "/auth/login", json_data={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self):
        resp = await _api("POST", "/auth/login", json_data={"username": "noone", "password": "pass"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_success(self):
        login_resp = await _api("POST", "/auth/login", json_data={"username": "admin", "password": "admin"})
        rt = login_resp.json()["refresh_token"]
        resp = await _api("POST", "/auth/refresh", json_data={"refresh_token": rt})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self):
        resp = await _api("POST", "/auth/refresh", json_data={"refresh_token": "bad"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(self):
        resp = await _api("POST", "/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


# =============================================================================
# API: Bearer Token Auth
# =============================================================================

class TestAuthAPIBearer:
    @pytest.mark.asyncio
    async def test_me_with_bearer_token(self):
        login_resp = await _api("POST", "/auth/login", json_data={"username": "admin", "password": "admin"})
        at = login_resp.json()["access_token"]
        resp = await _api("GET", "/auth/me", headers=_auth_header(at))
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["is_authenticated"] is True

    @pytest.mark.asyncio
    async def test_me_with_bad_bearer(self):
        resp = await _api("GET", "/auth/me", headers=_auth_header("bad.token"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_authenticated"] is False

    @pytest.mark.asyncio
    async def test_me_without_auth(self):
        resp = await _api("GET", "/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_authenticated"] is False

    @pytest.mark.asyncio
    async def test_x_user_id_header_is_ignored_by_default(self):
        """X-User-ID is trusted input, so it must not authenticate unless explicitly armed."""
        resp = await _api("GET", "/auth/me", headers={"X-User-ID": "user-admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_authenticated"] is False

    @pytest.mark.asyncio
    async def test_x_user_id_header_used_forged_admin_when_armed(self, monkeypatch):
        """Documents the opt-in: all three switches on -> header is honoured for local dev."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "auth_allow_dev_user_header", True)
        monkeypatch.setattr(settings, "debug", True)
        monkeypatch.setattr(settings, "app_env", "development")

        resp = await _api("GET", "/auth/me", headers={"X-User-ID": "user-admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_authenticated"] is True
        assert data["username"] == "admin"

    @pytest.mark.asyncio
    async def test_x_user_id_header_stays_off_in_production(self, monkeypatch):
        """Even with the flag on, a production APP_ENV must refuse the header."""
        from app.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "auth_allow_dev_user_header", True)
        monkeypatch.setattr(settings, "debug", False)
        monkeypatch.setattr(settings, "app_env", "production")

        resp = await _api("GET", "/auth/me", headers={"X-User-ID": "user-admin"})
        assert resp.status_code == 200
        assert resp.json()["is_authenticated"] is False


# =============================================================================
# API: Tenant Endpoints
# =============================================================================

class TestTenantAPI:
    @pytest.mark.asyncio
    async def test_create_tenant(self):
        resp = await _api("POST", "/auth/tenants", json_data={"name": "ApiOrg", "slug": "api-org"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "ApiOrg"

    @pytest.mark.asyncio
    async def test_list_tenants(self):
        resp = await _api("GET", "/auth/tenants")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_tenant(self):
        resp = await _api("GET", "/auth/tenants/tenant-default")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "default"

    @pytest.mark.asyncio
    async def test_get_tenant_not_found(self):
        resp = await _api("GET", "/auth/tenants/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_user_with_tenant(self):
        resp = await _api("POST", "/auth/users", json_data={
            "username": "tenantuser", "email": "tu@t.com", "password": "pw",
            "tenant_ids": ["tenant-default"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "tenant-default" in data["tenant_ids"]

    @pytest.mark.asyncio
    async def test_login_with_tenant(self):
        resp = await _api("POST", "/auth/login", json_data={
            "username": "admin", "password": "admin", "tenant_id": "tenant-default",
        })
        assert resp.status_code == 200


# =============================================================================
# Tenant Isolation
# =============================================================================

class TestTenantIsolation:
    def test_user_list_filtered_by_tenant(self):
        svc = get_auth_service()
        t1 = svc.create_tenant("OrgA", "org-a")
        t2 = svc.create_tenant("OrgB", "org-b")
        u1 = svc.create_user("user_a", "a@org.com", tenant_ids=[t1.id])
        u2 = svc.create_user("user_b", "b@org.com", tenant_ids=[t2.id])

        org_a_users = svc.list_users(tenant_id=t1.id)
        org_b_users = svc.list_users(tenant_id=t2.id)

        assert any(u.id == u1.id for u in org_a_users)
        assert not any(u.id == u2.id for u in org_a_users)
        assert any(u.id == u2.id for u in org_b_users)


# =============================================================================
# AuthContext tenant_id
# =============================================================================

class TestAuthContextTenant:
    def test_auth_context_has_tenant_id(self):
        svc = get_auth_service()
        ctx = svc.get_auth_context(user_id="user-admin", tenant_id="tenant-1")
        assert ctx.tenant_id == "tenant-1"

    def test_auth_context_to_dict_includes_tenant(self):
        ctx = AuthContext(
            user_id="u1", username="test", roles=["admin"],
            permissions=["task:read"], tenant_id="tenant-default",
            is_authenticated=True, request_id="req-1",
        )
        d = ctx.to_dict()
        assert d["tenant_id"] == "tenant-default"
        assert "tenant_id" in d
# =============================================================================
# Extended JWT Tests
# =============================================================================

class TestJWTExtended:
    def test_access_token_default_tenant_empty(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("u1")
        payload = mgr.decode_token(token)
        assert payload["tenant_id"] == ""

    def test_refresh_token_default_tenant_empty(self):
        mgr = get_jwt_manager()
        token = mgr.create_refresh_token("u1")
        payload = mgr.decode_token(token)
        assert payload["tenant_id"] == ""

    def test_token_with_all_fields(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("user-99", "tenant-99", "testuser", extra_claims={"scope": "admin", "aud": "workbench"})
        payload = mgr.decode_token(token)
        assert payload["sub"] == "user-99"
        assert payload["tenant_id"] == "tenant-99"
        assert payload["username"] == "testuser"
        assert payload["scope"] == "admin"

    def test_validate_access_token_with_none(self):
        mgr = get_jwt_manager()
        assert mgr.validate_access_token("") is None
        assert mgr.validate_access_token("not.a.jwt") is None

    def test_deleted_token_is_invalid(self):
        mgr = get_jwt_manager()
        assert mgr.decode_token_safe("eyJ.definitely.not.valid") is None


# =============================================================================
# Extended AuthService Tests
# =============================================================================

class TestAuthServiceExtended:
    def test_create_user_default_tenant_and_password(self):
        svc = AuthService()
        user = svc.create_user("minimal", "min@t.com")
        assert user.hashed_password == ""
        assert user.tenant_ids == []

    def test_update_user_add_tenant(self):
        svc = AuthService()
        user = svc.create_user("addtenant", "at@t.com")
        updated = svc.update_user(user.id, tenant_ids=["tenant-default", "new-tenant"])
        assert len(updated.tenant_ids) == 2

    def test_authenticate_empty_password(self):
        svc = AuthService()
        user = svc.create_user("nopass", "np@t.com")
        result = svc.authenticate("nopass", "")
        assert result is None

    def test_resolve_permissions_tenant_unaware(self):
        svc = AuthService()
        perms = svc.resolve_permissions(["role-admin"])
        assert len(perms) > 0

    def test_get_auth_context_with_tenant(self):
        svc = AuthService()
        ctx = svc.get_auth_context(user_id="user-admin", tenant_id="custom-tenant")
        assert ctx.tenant_id == "custom-tenant"

    def test_get_auth_context_unknown_user(self):
        svc = AuthService()
        ctx = svc.get_auth_context(user_id="nonexistent-user")
        assert ctx.is_authenticated is False
        assert ctx.username == "unknown"

    def test_resolve_user_info_returns_dict(self):
        svc = AuthService()
        info = svc.resolve_user_info("user-admin")
        assert "username" in info
        assert "roles" in info

    def test_clear_restores_defaults(self):
        svc = AuthService()
        svc.create_user("clearme", "c@t.com")
        svc.clear()
        users = svc.list_users()
        assert len(users) == 1
        assert users[0].username == "admin"
        tenants = svc.list_tenants()
        assert len(tenants) == 1
        assert tenants[0].slug == "default"


# =============================================================================
# Extended Tenant Tests
# =============================================================================

class TestTenantExtended:
    def test_update_tenant_is_active(self):
        svc = AuthService()
        t = svc.create_tenant("ActiveTest", "active-test")
        updated = svc.update_tenant(t.id, is_active=False)
        assert updated.is_active is False

    def test_update_tenant_not_found(self):
        svc = AuthService()
        assert svc.update_tenant("fake", name="x") is None

    def test_delete_tenant_not_found(self):
        svc = AuthService()
        assert svc.delete_tenant("fake") is False

    def test_get_tenant_by_slug_not_found(self):
        svc = AuthService()
        assert svc.get_tenant_by_slug("nonexistent") is None

    def test_list_roles_by_tenant(self):
        svc = AuthService()
        t = svc.create_tenant("RoleTenant", "role-tenant")
        svc.create_role("tenant-role", "Tenant-specific", ["task:read"], tenant_id=t.id)
        roles = svc.list_roles(tenant_id=t.id)
        assert len(roles) >= 1
        assert any(r.name == "tenant-role" for r in roles)

    def test_list_roles_all_includes_global(self):
        svc = AuthService()
        roles = svc.list_roles()
        names = [r.name for r in roles]
        assert "admin" in names


# =============================================================================
# Extended API Tests
# =============================================================================

class TestAuthAPIExtendedLogin:
    @pytest.mark.asyncio
    async def test_login_returns_valid_access_token(self):
        resp = await _api("POST", "/auth/login", json_data={"username": "admin", "password": "admin"})
        at = resp.json()["access_token"]
        me_resp = await _api("GET", "/auth/me", headers=_auth_header(at))
        assert me_resp.json()["username"] == "admin"

    @pytest.mark.asyncio
    async def test_refresh_gives_new_tokens(self):
        login_resp = await _api("POST", "/auth/login", json_data={"username": "admin", "password": "admin"})
        old_at = login_resp.json()["access_token"]
        rt = login_resp.json()["refresh_token"]
        refresh_resp = await _api("POST", "/auth/refresh", json_data={"refresh_token": rt})
        new_at = refresh_resp.json()["access_token"]
        assert new_at != old_at

    @pytest.mark.asyncio
    async def test_bearer_token_with_tenant_info(self):
        login_resp = await _api("POST", "/auth/login", json_data={
            "username": "admin", "password": "admin", "tenant_id": "tenant-default",
        })
        at = login_resp.json()["access_token"]
        me_resp = await _api("GET", "/auth/me", headers=_auth_header(at))
        data = me_resp.json()
        assert data["tenant_id"] == "tenant-default"

    @pytest.mark.asyncio
    async def test_list_users_with_tenant_filter_api(self):
        resp = await _api("GET", "/auth/users", params={"tenant_id": "tenant-default"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_create_role_with_tenant(self):
        resp = await _api("POST", "/auth/roles", json_data={
            "name": "api-tenant-role", "description": "API tenant role",
            "permissions": ["task:read"], "tenant_id": "tenant-default",
        })
        assert resp.status_code == 201
        assert resp.json()["tenant_id"] == "tenant-default"

    @pytest.mark.asyncio
    async def test_login_empty_body(self):
        resp = await _api("POST", "/auth/login", json_data={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_refresh_empty_body(self):
        resp = await _api("POST", "/auth/refresh", json_data={})
        assert resp.status_code == 422
# =============================================================================
# Final edge case tests
# =============================================================================

class TestEdgeCase:
    def test_empty_roles_permission_resolution(self):
        svc = AuthService()
        perms = svc.resolve_permissions([])
        assert perms == []

    def test_create_role_empty_permissions(self):
        svc = AuthService()
        role = svc.create_role("empty-perm", "No permissions", [])
        assert role.permissions == []

    def test_login_with_empty_tenant_uses_default(self):
        svc = AuthService()
        pair = svc.login("admin", "admin")
        assert pair is not None
        jwt_mgr = get_jwt_manager()
        payload = jwt_mgr.decode_token(pair.access_token)
        assert payload["tenant_id"] == "tenant-default"

    def test_auth_context_roles_empty(self):
        ctx = AuthContext(user_id="x", username="x", roles=[], is_authenticated=True)
        assert ctx.roles == []

    def test_token_pair_defaults(self):
        tp = TokenPair(access_token="a", refresh_token="b")
        assert tp.token_type == "bearer"
        assert tp.expires_in == 900

    def test_verify_password_empty_hashed(self):
        assert verify_password("anything", "") is False

    def test_hash_and_verify_unicode_password(self):
        h = hash_password("密码123!@#")
        assert verify_password("密码123!@#", h) is True

    @pytest.mark.asyncio
    async def test_api_create_tenant_default_metadata(self):
        resp = await _api("POST", "/auth/tenants", json_data={"name": "EdgeTenant"})
        data = resp.json()
        assert data["metadata"] == {}

    @pytest.mark.asyncio
    async def test_api_check_permission_with_bearer(self):
        login_resp = await _api("POST", "/auth/login", json_data={"username": "admin", "password": "admin"})
        at = login_resp.json()["access_token"]
        resp = await _api("GET", "/auth/permissions/check", params={"permission": "task:read"}, headers=_auth_header(at))
        assert resp.status_code == 200
        assert resp.json()["has_permission"] is True

    @pytest.mark.asyncio
    async def test_api_users_list_no_tenant_filter(self):
        resp = await _api("GET", "/auth/users")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1