"""
Phase 4.24 tests - APIKeyManager
Covers: create, validate, list, revoke, delete, tenant isolation
"""
import pytest
from app.openapi.api_keys import APIKeyManager, get_api_key_manager, reset_api_key_manager
from app.openapi.models import APIKey


@pytest.fixture(autouse=True)
def _reset():
    reset_api_key_manager()
    yield
    reset_api_key_manager()


@pytest.fixture
def manager():
    return APIKeyManager()


class TestAPIKeyCreation:
    def test_create_key(self, manager):
        key, raw = manager.create_key("test-key")
        assert key.name == "test-key"
        assert raw.startswith("ak-")
        assert len(raw) > 20
        assert key.key_prefix

    def test_create_key_with_tenant(self, manager):
        key, raw = manager.create_key("tenant-key", tenant_id="t1")
        assert key.tenant_id == "t1"

    def test_create_key_with_permissions(self, manager):
        key, raw = manager.create_key("perm-key", permissions=["read", "write"])
        assert "read" in key.permissions
        assert "write" in key.permissions

    def test_create_key_unique_raw(self, manager):
        _, r1 = manager.create_key("k1")
        _, r2 = manager.create_key("k2")
        assert r1 != r2

    def test_create_key_unique_ids(self, manager):
        k1, _ = manager.create_key("k1")
        k2, _ = manager.create_key("k2")
        assert k1.id != k2.id


class TestAPIKeyValidation:
    def test_validate_valid_key(self, manager):
        key, raw = manager.create_key("valid")
        validated = manager.validate_key(raw)
        assert validated is not None
        assert validated.id == key.id

    def test_validate_invalid_key(self, manager):
        validated = manager.validate_key("not-a-real-key")
        assert validated is None

    def test_validate_revoked_key(self, manager):
        key, raw = manager.create_key("temp")
        manager.revoke_key(key.id)
        validated = manager.validate_key(raw)
        assert validated is None

    def test_validate_updates_last_used(self, manager):
        key, raw = manager.create_key("used")
        validated = manager.validate_key(raw)
        assert validated.last_used_at is not None


class TestAPIKeyListing:
    def test_list_all(self, manager):
        manager.create_key("k1")
        manager.create_key("k2")
        keys = manager.list_keys()
        assert len(keys) == 2

    def test_list_by_tenant(self, manager):
        manager.create_key("k1", tenant_id="t1")
        manager.create_key("k2", tenant_id="t2")
        t1_keys = manager.list_keys(tenant_id="t1")
        assert len(t1_keys) == 1
        assert t1_keys[0]["name"] == "k1"

    def test_list_empty(self, manager):
        keys = manager.list_keys()
        assert keys == []


class TestAPIKeyRevocation:
    def test_revoke(self, manager):
        key, _ = manager.create_key("to-revoke")
        assert manager.revoke_key(key.id) is True
        assert manager.get_key(key.id).enabled is False

    def test_revoke_nonexistent(self, manager):
        assert manager.revoke_key("nonexistent") is False

    def test_delete(self, manager):
        key, _ = manager.create_key("to-delete")
        assert manager.delete_key(key.id) is True
        assert manager.get_key(key.id) is None

    def test_delete_nonexistent(self, manager):
        assert manager.delete_key("nonexistent") is False


class TestAPIKeyTenantIsolation:
    def test_belongs_to_tenant(self, manager):
        key, _ = manager.create_key("t-key", tenant_id="t1")
        assert manager.belongs_to_tenant(key.id, "t1") is True
        assert manager.belongs_to_tenant(key.id, "t2") is False

    def test_belongs_to_tenant_nonexistent(self, manager):
        assert manager.belongs_to_tenant("nonexistent", "t1") is False


class TestAPIKeySingleton:
    def test_singleton(self):
        a = get_api_key_manager()
        b = get_api_key_manager()
        assert a is b

    def test_reset(self):
        a = get_api_key_manager()
        reset_api_key_manager()
        b = get_api_key_manager()
        assert a is not b


class TestAPIKeyModel:
    def test_to_dict(self):
        key, _ = get_api_key_manager().create_key("model-key", permissions=["read"])
        d = key.to_dict()
        assert d["name"] == "model-key"
        assert d["permissions"] == ["read"]
        assert "key_prefix" in d
        assert "key_hash" not in d  # hash not exposed

    def test_default_permissions(self):
        key, _ = get_api_key_manager().create_key("default-perm")
        assert key.permissions == ["read"]

class TestAPIKeyEdgeCases:
    def test_create_key_empty_name(self, manager):
        key, raw = manager.create_key("")
        assert key.name == ""

    def test_create_key_no_permissions(self, manager):
        key, raw = manager.create_key("no-perm", permissions=[])
        assert key.permissions == []

    def test_list_after_delete(self, manager):
        k1, _ = manager.create_key("k1")
        k2, _ = manager.create_key("k2")
        manager.delete_key(k1.id)
        keys = manager.list_keys()
        assert len(keys) == 1

    def test_validate_after_delete(self, manager):
        key, raw = manager.create_key("temp")
        manager.delete_key(key.id)
        validated = manager.validate_key(raw)
        assert validated is None

    def test_multiple_keys_same_tenant(self, manager):
        manager.create_key("k1", tenant_id="t1")
        manager.create_key("k2", tenant_id="t1")
        manager.create_key("k3", tenant_id="t1")
        keys = manager.list_keys(tenant_id="t1")
        assert len(keys) == 3

    def test_key_to_dict_no_hash_leak(self, manager):
        key, _ = manager.create_key("safe")
        d = key.to_dict()
        assert "key_hash" not in d
        assert "raw_key" not in d