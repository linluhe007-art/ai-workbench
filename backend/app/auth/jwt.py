"""
JWT Token Manager - access & refresh token handling.

Uses python-jose for JWT encode/decode.
Phase 4.15: Production Security & Multi-Tenant Foundation.
"""

from datetime import datetime, timezone, timedelta
from typing import Any

from jose import jwt, JWTError

from app.config import get_settings
from app.utils.logger import get_logger
import os


logger = get_logger(__name__)


class JWTManager:
    """Manages JWT access and refresh token creation and validation."""

    def __init__(self):
        settings = get_settings()
        self._secret_key = settings.effective_jwt_secret if hasattr(settings, "effective_jwt_secret") else settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm
        self._access_expire_minutes = settings.auth_access_token_expire_minutes or settings.jwt_access_token_expire_minutes
        self._refresh_expire_days = settings.auth_refresh_token_expire_days or settings.jwt_refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str = "",
        username: str = "",
        extra_claims: dict | None = None,
    ) -> str:
        """Create a short-lived access token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self._access_expire_minutes)
        claims = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "username": username,
            "type": "access",
            "iat": now,
            "exp": expire,
        }
        if extra_claims:
            claims.update(extra_claims)
        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        tenant_id: str = "",
    ) -> str:
        """Create a long-lived refresh token."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self._refresh_expire_days)
        claims = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "type": "refresh",
            "iat": now,
            "exp": expire,
        }
        return jwt.encode(claims, self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token. Raises JWTError on failure."""
        return jwt.decode(token, self._secret_key, algorithms=[self._algorithm])

    def decode_token_safe(self, token: str) -> dict[str, Any] | None:
        """Decode token, returning None on any error."""
        try:
            return self.decode_token(token)
        except JWTError:
            return None

    def validate_access_token(self, token: str) -> dict[str, Any] | None:
        """Validate an access token specifically."""
        payload = self.decode_token_safe(token)
        if payload is None:
            return None
        if payload.get("type") != "access":
            return None
        return payload

    def validate_refresh_token(self, token: str) -> dict[str, Any] | None:
        """Validate a refresh token specifically."""
        payload = self.decode_token_safe(token)
        if payload is None:
            return None
        if payload.get("type") != "refresh":
            return None
        return payload

    def is_token_expired(self, token: str) -> bool:
        """Check if a token is expired (without throwing)."""
        return self.decode_token_safe(token) is None


# Global singleton
_jwt_manager: JWTManager | None = None


def get_jwt_manager() -> JWTManager:
    """Get or create the global JWTManager singleton."""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


def reset_jwt_manager() -> None:
    """Reset the global JWTManager (for testing)."""
    global _jwt_manager
    _jwt_manager = None