"""Unified API error response model."""

from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorCode:
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    INVALID_TASK_STATE = "INVALID_TASK_STATE"
    TASK_ALREADY_COMPLETED = "TASK_ALREADY_COMPLETED"
    TASK_ALREADY_RUNNING = "TASK_ALREADY_RUNNING"
    TASK_ALREADY_CANCELLED = "TASK_ALREADY_CANCELLED"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    TASK_CONTROL_CONFLICT = "TASK_CONTROL_CONFLICT"
    QUEUE_FULL = "QUEUE_FULL"
    TASK_RETRY_EXHAUSTED = "TASK_RETRY_EXHAUSTED"
    INVALID_REQUEST = "INVALID_REQUEST"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    ROLE_NOT_FOUND = "ROLE_NOT_FOUND"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"


def error_response(
    code: str,
    message: str,
    details: dict | None = None,
    request_id: str | None = None,
    status_code: int = 400,
) -> JSONResponse:
    """Build a unified error JSON response."""
    body: dict[str, Any] = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }
    if request_id:
        body["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=body)


def task_not_found(task_id: str, request_id: str | None = None) -> JSONResponse:
    return error_response(
        ErrorCode.TASK_NOT_FOUND,
        f"Task not found: {task_id}",
        {"task_id": task_id},
        request_id,
        404,
    )


def invalid_state(current: str, action: str, request_id: str | None = None) -> JSONResponse:
    return error_response(
        ErrorCode.INVALID_TASK_STATE,
        f"Cannot {action} task in state {current}",
        {"current_state": current, "action": action},
        request_id,
        409,
    )