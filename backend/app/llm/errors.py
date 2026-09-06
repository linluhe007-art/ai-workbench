"""LLM-specific application errors (Phase Beta-LLM)."""

from __future__ import annotations

from typing import Any

from app.utils.errors import AppError, ErrorCode


class LLMError(AppError):
    default_message = "LLM provider error"
    error_code = ErrorCode.LLM_PROVIDER_ERROR
    status_code = 502


class LLMNotConfiguredError(LLMError):
    default_message = "LLM provider is not configured"
    error_code = ErrorCode.LLM_NOT_CONFIGURED
    status_code = 503


class LLMAuthError(LLMError):
    default_message = "LLM authentication failed"
    error_code = ErrorCode.LLM_AUTH_FAILED
    status_code = 401


class LLMRateLimitError(LLMError):
    default_message = "LLM provider rate limit exceeded"
    error_code = ErrorCode.LLM_RATE_LIMITED
    status_code = 429


class LLMTimeoutError(LLMError):
    default_message = "LLM provider request timed out"
    error_code = ErrorCode.LLM_TIMEOUT
    status_code = 504


class LLMProviderError(LLMError):
    default_message = "LLM provider request failed"
    error_code = ErrorCode.LLM_PROVIDER_ERROR
    status_code = 502
