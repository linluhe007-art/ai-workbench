"""Tests for the Phase Beta-LLM API endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware import RequestIDMiddleware
from app.api.v1.llm import router
from app.llm.deepseek import DeepSeekProvider
from app.llm.provider import MockLLMProvider
from app.utils.errors import install_exception_handlers


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    app.include_router(router)
    install_exception_handlers(app)
    return TestClient(app)


class TestLLMConfigAPI:
    def test_config_returns_success(self, client):
        response = client.get("/llm/config")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_config_has_provider(self, client):
        data = client.get("/llm/config").json()
        assert data["provider"] in ("deepseek", "openai", "mock")

    def test_config_has_model(self, client):
        data = client.get("/llm/config").json()
        assert "model" in data

    def test_config_has_configured_flag(self, client):
        data = client.get("/llm/config").json()
        assert isinstance(data["configured"], bool)

    def test_config_has_supported_providers(self, client):
        data = client.get("/llm/config").json()
        assert "supported_providers" in data


class TestLLMTestAPISuccess:
    @pytest.fixture
    def mock_provider(self, monkeypatch):
        provider = MockLLMProvider(default_model="deepseek-chat")
        monkeypatch.setattr("app.api.v1.llm.get_llm_provider", lambda: provider)
        return provider

    def test_test_returns_success(self, client, mock_provider):
        response = client.post("/llm/test", json={"prompt": "hello"})
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_test_returns_content(self, client, mock_provider):
        data = client.post("/llm/test", json={"prompt": "hello"}).json()
        assert data["content"]

    def test_test_returns_model(self, client, mock_provider):
        data = client.post("/llm/test", json={"prompt": "hello"}).json()
        assert data["model"] == "deepseek-chat"

    def test_test_returns_token_fields(self, client, mock_provider):
        data = client.post("/llm/test", json={"prompt": "hello"}).json()
        assert "input_tokens" in data
        assert "output_tokens" in data

    def test_test_returns_latency(self, client, mock_provider):
        data = client.post("/llm/test", json={"prompt": "hello"}).json()
        assert "latency_ms" in data

    def test_test_passes_model_override(self, client, mock_provider, monkeypatch):
        captured = {}
        async def fake_generate(messages, model=None, temperature=0.2, max_tokens=4000, **kwargs):
            captured["model"] = model
            from app.llm.models import LLMResponse
            return LLMResponse(content="ok", model=model or "deepseek-chat")
        monkeypatch.setattr(mock_provider, "generate", fake_generate)
        client.post("/llm/test", json={"prompt": "x", "model": "deepseek-reasoner"})
        assert captured["model"] == "deepseek-reasoner"


class TestLLMTestAPIErrors:
    @pytest.fixture
    def unconfigured_provider(self, monkeypatch):
        provider = DeepSeekProvider(api_key="")
        monkeypatch.setattr("app.api.v1.llm.get_llm_provider", lambda: provider)
        return provider

    def test_unconfigured_returns_503(self, client, unconfigured_provider):
        response = client.post("/llm/test", json={"prompt": "hello"})
        assert response.status_code == 503

    def test_unconfigured_has_error_code(self, client, unconfigured_provider):
        data = client.post("/llm/test", json={"prompt": "hello"}).json()
        assert data["error_code"] == "LLM_NOT_CONFIGURED"

    def test_unconfigured_has_success_false(self, client, unconfigured_provider):
        data = client.post("/llm/test", json={"prompt": "hello"}).json()
        assert data["success"] is False

    def test_unconfigured_has_request_id(self, client, unconfigured_provider):
        data = client.post("/llm/test", json={"prompt": "hello"}, headers={"X-Request-ID": "req-1"}).json()
        assert data["request_id"] == "req-1"

    def test_validation_error_shape(self, client):
        response = client.post("/llm/test", json={"temperature": "not-a-number"})
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_validation_error_has_request_id(self, client):
        response = client.post("/llm/test", json={"temperature": "not-a-number"}, headers={"X-Request-ID": "req-2"})
        assert response.json()["request_id"] == "req-2"


class TestLLMAPIEdgeCases:
    def test_config_api_key_set_is_boolean(self, client):
        data = client.get("/llm/config").json()
        assert isinstance(data["api_key_set"], bool)

    def test_config_configured_is_boolean(self, client):
        data = client.get("/llm/config").json()
        assert isinstance(data["configured"], bool)

    def test_config_supported_providers_has_mock(self, client):
        data = client.get("/llm/config").json()
        assert "mock" in data["supported_providers"]

    def test_test_default_prompt_succeeds(self, client, monkeypatch):
        monkeypatch.setattr("app.api.v1.llm.get_llm_provider", lambda: MockLLMProvider(default_model="deepseek-chat"))
        response = client.post("/llm/test", json={})
        assert response.status_code == 200
        assert response.json()["success"] is True

