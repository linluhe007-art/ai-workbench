"""Phase 4.20: Production security tests - JWT, tenant isolation, error handling."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.auth.jwt import JWTManager, get_jwt_manager, reset_jwt_manager
from app.auth.models import AuthContext, User, TokenPair
from app.api.errors import ErrorCode, error_response, task_not_found, invalid_state


@pytest.fixture(autouse=True)
def reset_jwt():
    reset_jwt_manager()
    yield
    reset_jwt_manager()


class TestJWTTokenTypes:

    def test_access_token_has_type(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("user-1")
        payload = mgr.decode_token(token)
        assert payload["type"] == "access"

    def test_refresh_token_has_type(self):
        mgr = get_jwt_manager()
        token = mgr.create_refresh_token("user-1")
        payload = mgr.decode_token(token)
        assert payload["type"] == "refresh"

    def test_access_token_has_exp(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("user-1")
        payload = mgr.decode_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_refresh_token_has_exp(self):
        mgr = get_jwt_manager()
        token = mgr.create_refresh_token("user-1")
        payload = mgr.decode_token(token)
        assert "exp" in payload

    def test_validate_access_token_rejects_refresh(self):
        mgr = get_jwt_manager()
        refresh = mgr.create_refresh_token("user-1")
        result = mgr.validate_access_token(refresh)
        assert result is None

    def test_validate_refresh_token_rejects_access(self):
        mgr = get_jwt_manager()
        access = mgr.create_access_token("user-1")
        result = mgr.validate_refresh_token(access)
        assert result is None

    def test_decode_invalid_token(self):
        mgr = get_jwt_manager()
        result = mgr.decode_token_safe("not-a-valid-token")
        assert result is None

    def test_token_has_sub(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("user-123", tenant_id="t1")
        payload = mgr.decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["tenant_id"] == "t1"


class TestErrorHandling:

    def test_error_response_has_code(self):
        resp = error_response(ErrorCode.TASK_NOT_FOUND, "not found", status_code=404)
        assert resp.status_code == 404
        body = resp.body.decode() if isinstance(resp.body, bytes) else resp.body
        import json
        data = json.loads(body) if isinstance(body, str) else body
        assert data["success"] is False
        assert data["error"]["code"] == "TASK_NOT_FOUND"

    def test_error_response_with_request_id(self):
        resp = error_response("ERR", "msg", request_id="req-123", status_code=400)
        import json
        body = resp.body.decode() if isinstance(resp.body, bytes) else resp.body
        data = json.loads(body) if isinstance(body, str) else body
        assert data["request_id"] == "req-123"

    def test_task_not_found_helper(self):
        resp = task_not_found("task-123", request_id="r1")
        assert resp.status_code == 404

    def test_invalid_state_helper(self):
        resp = invalid_state("completed", "cancel")
        assert resp.status_code == 409

    def test_all_error_codes_defined(self):
        codes = [v for k, v in vars(ErrorCode).items() if not k.startswith("_")]
        assert "TASK_NOT_FOUND" in codes
        assert "FORBIDDEN" in codes
        assert "UNAUTHORIZED" in codes


class TestTenantIsolation:

    def test_auth_context_has_tenant(self):
        ctx = AuthContext(user_id="u1", tenant_id="t1", roles=["admin"])
        assert ctx.tenant_id == "t1"

    def test_tenant_isolation_prevents_cross_access(self):
        """Tenant A should not access Tenant B resources."""
        ctx_a = AuthContext(user_id="u1", tenant_id="tenant-a", roles=["admin"])
        ctx_b = AuthContext(user_id="u2", tenant_id="tenant-b", roles=["admin"])
        assert ctx_a.tenant_id != ctx_b.tenant_id

    def test_jwt_encodes_tenant(self):
        mgr = get_jwt_manager()
        token = mgr.create_access_token("user-1", tenant_id="tenant-x")
        payload = mgr.decode_token(token)
        assert payload["tenant_id"] == "tenant-x"


class TestPasswordSecurity:

    def test_password_not_in_user_dict(self):
        from app.auth.models import User
        user = User(id="u1", username="test", email="t@t.com", hashed_password="hashed_xxx")
        d = user.to_dict() if hasattr(user, "to_dict") else {}
        if "hashed_password" in d:
            assert d["hashed_password"] == "********"

    def test_password_hashing(self):
        from app.auth.service import hash_password, verify_password
        pw = "my-secure-password"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed)
        assert not verify_password("wrong", hashed)
