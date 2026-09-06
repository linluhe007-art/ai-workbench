"""Tests for the unified API error handling layer (Phase Beta-LLM)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware import RequestIDMiddleware
from app.utils.errors import (
    AppError,
    ErrorCode,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    ValidationFailedError,
    install_exception_handlers,
)


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/app-error")
    async def app_error():
        raise AppError(message="bad request", error_code="CUSTOM_ERROR", status_code=400, details={"field": "name"})

    @app.get("/not-found")
    async def not_found():
        raise NotFoundError(message="task gone")

    @app.get("/forbidden")
    async def forbidden():
        raise PermissionDeniedError()

    @app.get("/http-error")
    async def http_error():
        raise StarletteHTTPException(status_code=404, detail="raw not found")

    @app.get("/boom")
    async def boom():
        raise RuntimeError("sensitive detail")

    @app.get("/items/{item_id}")
    async def item(item_id: int):
        return {"item_id": item_id}

    install_exception_handlers(app)
    return TestClient(app)


class TestAppError:
    def test_default_message(self):
        error = AppError()
        assert error.message == "Server error"

    def test_custom_message(self):
        error = AppError(message="custom")
        assert error.message == "custom"

    def test_to_dict(self):
        error = AppError(message="x", error_code="E1", details={"a": 1})
        data = error.to_dict("req-1")
        assert data["success"] is False
        assert data["error_code"] == "E1"
        assert data["request_id"] == "req-1"
        assert data["details"] == {"a": 1}

    def test_subclass_status_codes(self):
        assert NotFoundError().status_code == 404
        assert PermissionDeniedError().status_code == 403
        assert ValidationFailedError().status_code == 422
        assert InternalServerError().status_code == 500


class TestErrorCodes:
    def test_internal_error(self):
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"

    def test_validation_error(self):
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"

    def test_not_found(self):
        assert ErrorCode.NOT_FOUND == "NOT_FOUND"

    def test_permission_denied(self):
        assert ErrorCode.PERMISSION_DENIED == "PERMISSION_DENIED"

    def test_task_not_found(self):
        assert ErrorCode.TASK_NOT_FOUND == "TASK_NOT_FOUND"

    def test_search_provider_error(self):
        assert ErrorCode.SEARCH_PROVIDER_ERROR == "SEARCH_PROVIDER_ERROR"

    def test_llm_codes(self):
        assert ErrorCode.LLM_NOT_CONFIGURED == "LLM_NOT_CONFIGURED"
        assert ErrorCode.LLM_AUTH_FAILED == "LLM_AUTH_FAILED"
        assert ErrorCode.LLM_RATE_LIMITED == "LLM_RATE_LIMITED"
        assert ErrorCode.LLM_TIMEOUT == "LLM_TIMEOUT"
        assert ErrorCode.LLM_PROVIDER_ERROR == "LLM_PROVIDER_ERROR"


class TestErrorResponseShape:
    def test_app_error_shape(self, client):
        response = client.get("/app-error")
        data = response.json()
        assert data["success"] is False
        assert data["error_code"] == "CUSTOM_ERROR"
        assert data["message"] == "bad request"

    def test_app_error_request_id(self, client):
        response = client.get("/app-error", headers={"X-Request-ID": "req-123"})
        assert response.json()["request_id"] == "req-123"

    def test_app_error_details(self, client):
        response = client.get("/app-error")
        assert response.json()["details"] == {"field": "name"}

    def test_not_found_status(self, client):
        assert client.get("/not-found").status_code == 404

    def test_not_found_code(self, client):
        assert client.get("/not-found").json()["error_code"] == "NOT_FOUND"

    def test_forbidden_status(self, client):
        assert client.get("/forbidden").status_code == 403

    def test_forbidden_code(self, client):
        assert client.get("/forbidden").json()["error_code"] == "PERMISSION_DENIED"


class TestFrameworkErrors:
    def test_http_exception_status(self, client):
        assert client.get("/http-error").status_code == 404

    def test_http_exception_shape(self, client):
        data = client.get("/http-error").json()
        assert data["success"] is False
        assert data["error_code"] == "NOT_FOUND"

    def test_validation_status(self, client):
        assert client.get("/items/not-an-int").status_code == 422

    def test_validation_code(self, client):
        assert client.get("/items/not-an-int").json()["error_code"] == "VALIDATION_ERROR"

    def test_validation_request_id(self, client):
        data = client.get("/items/not-an-int", headers={"X-Request-ID": "req-v"}).json()
        assert data["request_id"] == "req-v"


class TestUnhandledErrors:
    def test_unhandled_status_is_500(self, client):
        assert client.get("/boom").status_code == 500

    def test_unhandled_code_is_internal(self, client):
        assert client.get("/boom").json()["error_code"] == "INTERNAL_ERROR"

    def test_unhandled_does_not_leak_detail(self, client):
        data = client.get("/boom").json()
        assert "sensitive detail" not in str(data)

    def test_unhandled_has_request_id(self, client):
        data = client.get("/boom", headers={"X-Request-ID": "req-500"}).json()
        assert data["request_id"] == "req-500"


class TestErrorHandlingMore:
    def test_app_error_default_status_code(self):
        assert AppError().status_code == 400

    def test_app_error_to_dict_without_request_id(self):
        data = AppError(message="x").to_dict()
        assert data["request_id"] == ""

    def test_internal_error_message(self):
        error = InternalServerError(message="boom")
        assert error.error_code == "INTERNAL_ERROR"
        assert error.status_code == 500

