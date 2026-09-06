"""
AuthMiddleware - injects AuthContext into every request.

Supports:
- Authorization: Bearer <jwt> (Phase 4.15)
- X-User-ID header (Phase 4.14, backwards compatible)
- X-Auth-Token header (future OAuth)
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.auth.service import get_auth_service
from app.api.middleware import get_request_id
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Injects AuthContext into request.state for every request.

    Resolution order:
    1. Authorization: Bearer <jwt> → decode JWT
    2. X-User-ID header → direct user lookup (dev only)
    3. X-Auth-Token header → (future: OAuth)
    4. Default → anonymous context
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        auth_service = get_auth_service()
        request_id = get_request_id(request)

        # 1. Bearer token (JWT)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            auth_context = auth_service.get_auth_context_from_token(
                token=token,
                request_id=request_id,
            )
            request.state.auth_context = auth_context
            response = await call_next(request)
            return response

        # 2. X-User-ID (dev backwards compat, disabled in production)
        from app.config import get_settings
        settings = get_settings()
        allow_dev_header = getattr(settings, "auth_allow_dev_user_header", True)
        if allow_dev_header:
            user_id = request.headers.get("X-User-ID")
            if user_id:
                auth_context = auth_service.get_auth_context(
                    user_id=user_id,
                    request_id=request_id,
                )
                request.state.auth_context = auth_context
                response = await call_next(request)
                return response

        # 3. X-Auth-Token (future OAuth)
        auth_token = request.headers.get("X-Auth-Token")
        if auth_token:
            auth_context = auth_service.get_auth_context(
                user_id=None,
                request_id=request_id,
            )
            request.state.auth_context = auth_context
            response = await call_next(request)
            return response

        # 4. Anonymous
        auth_context = auth_service.get_auth_context(
            user_id=None,
            request_id=request_id,
        )
        request.state.auth_context = auth_context
        response = await call_next(request)
        return response