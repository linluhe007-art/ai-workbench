"""
Structured JSON logger for Phase 4.21 observability.

Provides structured logging with fields:
  timestamp, level, request_id, tenant_id, user_id, task_id, agent_id, message

Usage:
    from app.observability.logger import get_observability_logger
    log = get_observability_logger()
    log.info("Task started", task_id="t1", agent_id="research")
"""
import json
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Context variables for request-scoped fields
_request_id_ctx: ContextVar = ContextVar("observability_request_id", default=None)
_tenant_id_ctx: ContextVar = ContextVar("observability_tenant_id", default=None)
_user_id_ctx: ContextVar = ContextVar("observability_user_id", default=None)


class ObservabilityLogger:
    """Structured JSON logger for observability."""

    def __init__(self, name: str = "observability", stream=None):
        self._name = name
        self._stream = stream or sys.stdout

    def _emit(self, level: str, message: str, **fields: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "logger": self._name,
            "message": message,
        }

        request_id = _request_id_ctx.get(None) or fields.pop("request_id", None)
        tenant_id = _tenant_id_ctx.get(None) or fields.pop("tenant_id", None)
        user_id = _user_id_ctx.get(None) or fields.pop("user_id", None)

        if request_id:
            record["request_id"] = request_id
        if tenant_id:
            record["tenant_id"] = tenant_id
        if user_id:
            record["user_id"] = user_id

        record.update(fields)

        try:
            self._stream.write(json.dumps(record, default=str) + "\n")
            self._stream.flush()
        except Exception:
            pass

    def info(self, message: str, **fields: Any) -> None:
        self._emit("INFO", message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._emit("WARNING", message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit("ERROR", message, **fields)

    def exception(self, message: str, exc_info: bool = True, **fields: Any) -> None:
        import traceback
        if exc_info:
            fields["traceback"] = traceback.format_exc()
        self._emit("ERROR", message, **fields)


# Singleton
_logger: ObservabilityLogger | None = None


def get_observability_logger() -> ObservabilityLogger:
    global _logger
    if _logger is None:
        _logger = ObservabilityLogger()
    return _logger


def reset_observability_logger() -> None:
    global _logger
    _logger = None


# Context setters
def set_request_context(request_id: str | None = None, tenant_id: str | None = None, user_id: str | None = None) -> None:
    if request_id:
        _request_id_ctx.set(request_id)
    if tenant_id:
        _tenant_id_ctx.set(tenant_id)
    if user_id:
        _user_id_ctx.set(user_id)


def clear_request_context() -> None:
    _request_id_ctx.set(None)
    _tenant_id_ctx.set(None)
    _user_id_ctx.set(None)