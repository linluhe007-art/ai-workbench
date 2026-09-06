"""
APIKeyManager - API key lifecycle management with SHA-256 hashing.
Phase 4.24: Secure key storage, permission binding, tenant isolation.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from app.openapi.models import APIKey
from app.utils.logger import get_logger

logger = get_logger(__name__)


class APIKeyManager:
    """
    Manages API key creation, validation, and revocation.

    Security:
    - Raw keys returned only once at creation time
    - SHA-256 hash stored; cannot recover raw key
    - Key prefix (first 8 chars) stored for display only
    - Tenant isolation enforced on all queries
    """

    def __init__(self):
        self._keys: dict[str, APIKey] = {}  # id -> APIKey
        self._hash_index: dict[str, str] = {}  # hash -> id

    # -- Creation --

    def create_key(
        self,
        name: str,
        tenant_id: str = "",
        created_by: str = "",
        permissions: list[str] | None = None,
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.

        Returns:
            (APIKey, raw_key) - raw_key only returned here; store securely.
        """
        raw_key = "ak-" + secrets.token_hex(24)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        prefix = raw_key[:11]  # "ak-" + first 8 hex chars

        api_key = APIKey(
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            permissions=permissions or ["read"],
            tenant_id=tenant_id,
            created_by=created_by,
        )

        self._keys[api_key.id] = api_key
        self._hash_index[key_hash] = api_key.id

        logger.info("API key created", key_id=api_key.id, name=name, tenant=tenant_id)
        return api_key, raw_key

    # -- Validation --

    def validate_key(self, raw_key: str) -> APIKey | None:
        """Validate a raw API key. Returns the APIKey if valid, None otherwise."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_id = self._hash_index.get(key_hash)
        if not key_id:
            return None

        api_key = self._keys.get(key_id)
        if not api_key or not api_key.enabled:
            return None

        api_key.last_used_at = datetime.now(timezone.utc)
        return api_key

    # -- Listing --

    def list_keys(self, tenant_id: str = "") -> list[dict]:
        """List API keys, optionally filtered by tenant."""
        results = []
        for key in self._keys.values():
            if tenant_id and key.tenant_id != tenant_id:
                continue
            results.append(key.to_dict())
        return results

    def get_key(self, key_id: str) -> APIKey | None:
        """Get a single API key by ID."""
        return self._keys.get(key_id)

    # -- Revocation --

    def revoke_key(self, key_id: str) -> bool:
        """Revoke (disable) an API key."""
        key = self._keys.get(key_id)
        if not key:
            return False
        key.enabled = False
        logger.info("API key revoked", key_id=key_id)
        return True

    def delete_key(self, key_id: str) -> bool:
        """Permanently delete an API key."""
        key = self._keys.pop(key_id, None)
        if key:
            self._hash_index.pop(key.key_hash, None)
            logger.info("API key deleted", key_id=key_id)
            return True
        return False

    # -- Tenant check --

    def belongs_to_tenant(self, key_id: str, tenant_id: str) -> bool:
        """Check if a key belongs to a tenant."""
        key = self._keys.get(key_id)
        return key is not None and key.tenant_id == tenant_id


# Singletons

_key_manager: APIKeyManager | None = None


def get_api_key_manager() -> APIKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager


def reset_api_key_manager() -> None:
    global _key_manager
    _key_manager = None