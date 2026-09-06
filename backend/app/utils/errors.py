"""Unified API error model and FastAPI exception handlers (Phase Beta-LLM)."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorCode:
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    SEARCH_PROVIDER_ERROR = "SEARCH_PROVIDER_ERROR"
    LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"
    LLM_AUTH_FAILED = "LLM_AUTH_FAILED"
    LLM_RATE_LIMITED = "LLM_RATE_LIMITED"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"


class AppError(Exception):
    """Base application error carrying a client-safe API response."""

    status_code: int = 400
    error_code: str = ErrorCode.INTERNAL_ERROR
    default_message: str = "Server error"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        super().__init__(self.message)

    def to_dict(self, request_id: str = "") -> dict[str, Any]:
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
            "request_id": request_id,
            "details": self.details,
        }


class NotFoundError(AppError):
    status_code = 404
    error_code = ErrorCode.NOT_FOUND
    default_message = "Resource not found"


class ValidationFailedError(AppError):
    status_code = 422
    error_code = ErrorCode.VALIDATION_ERROR
    default_message = "Validation failed"


class PermissionDeniedError(AppError):
    status_code = 403
    error_code = ErrorCode.PERMISSION_DENIED
    default_message = "Permission denied"


class InternalServerError(AppError):
    status_code = 500
    error_code = ErrorCode.INTERNAL_ERROR
    default_message = "Internal server error"


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "") or "")


def install_exception_handlers(app: FastAPI) -> None:
    """Install unified exception handlers on a FastAPI application."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(_request_id(request)),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.VALIDATION_ERROR
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        payload = AppError(message=message, status_code=exc.status_code, error_code=code).to_dict(_request_id(request))
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details: dict[str, Any] = {"errors": exc.errors()}
        payload = AppError(
            message="Request validation failed",
            details=details,
            status_code=422,
            error_code=ErrorCode.VALIDATION_ERROR,
        ).to_dict(_request_id(request))
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error")
        payload = AppError(
            message="Internal server error",
            status_code=500,
            error_code=ErrorCode.INTERNAL_ERROR,
        ).to_dict(_request_id(request))
        return JSONResponse(status_code=500, content=payload)
