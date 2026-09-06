"""
Permission checking and resource access control.
Phase 4.14: Provides require_permission, require_role decorators and helpers.
"""

from functools import wraps
from typing import Callable, Any

from fastapi import HTTPException, Request

from app.auth.models import PermissionType, AuthContext
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_auth_context(request: Request) -> AuthContext:
    """Extract auth context from request state (set by AuthMiddleware)."""
    return getattr(request.state, "auth_context", AuthContext(
        user_id="anonymous",
        username="anonymous",
        roles=[],
        is_authenticated=False,
    ))


def require_permission(permission: PermissionType):
    """
    Decorator for FastAPI endpoints that require a specific permission.
    Returns 403 if the user lacks the permission.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")
            if request is None:
                for arg in args:
                    if hasattr(arg, "state"):
                        request = arg
                        break

            if request is not None:
                ctx: AuthContext = get_auth_context(request)
                if not ctx.has_permission(permission):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "code": "FORBIDDEN",
                            "message": f"Missing permission: {permission.value}",
                            "required_permission": permission.value,
                        },
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permissions: list[PermissionType]):
    """Decorator requiring at least one of the listed permissions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")

            if request is not None:
                ctx: AuthContext = get_auth_context(request)
                if not ctx.has_any_permission(permissions):
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "code": "FORBIDDEN",
                            "message": "Missing required permissions",
                            "required_permissions": [p.value for p in permissions],
                        },
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_permission(ctx: AuthContext, permission: PermissionType) -> bool:
    """Synchronous permission check (for service layer)."""
    return ctx.has_permission(permission)


def check_resource_access(
    ctx: AuthContext,
    resource_owner_id: str | None = None,
    permission: PermissionType | None = None,
) -> bool:
    """
    Check if auth context has access to a resource.
    Admins always pass. Otherwise checks permission + ownership.
    """
    if ctx.has_permission(PermissionType.ADMIN_SYSTEM):
        return True
    if permission and not ctx.has_permission(permission):
        return False
    if resource_owner_id and ctx.user_id == resource_owner_id:
        return True
    if permission:
        return True
    return False