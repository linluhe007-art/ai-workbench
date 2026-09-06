"""Tests for the Phase Beta-LLM DeepSeek provider."""

import httpx
import pytest

from app.llm.deepseek import DeepSeekProvider, OpenAICompatibleProvider, OpenAIProvider
from app.llm.errors import (
    LLMAuthError,
    LLMNotConfiguredError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class FakeAsyncClient:
    last_payload = None
    response = FakeResponse()
    error = None

    def __init__(self, timeout=None):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        FakeAsyncClient.last_payload = {"url": url, "json": json, "headers": headers}
        if FakeAsyncClient.error is not None:
            raise FakeAsyncClient.error
        return FakeAsyncClient.response


@pytest.fixture
def fake_client(monkeypatch):
    FakeAsyncClient.last_payload = None
    FakeAsyncClient.response = FakeResponse()
    FakeAsyncClient.error = None
    monkeypatch.setattr("app.llm.deepseek.httpx.AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


class TestDeepSeekDefaults:
    def test_default_model(self):
        assert DeepSeekProvider().get_model_name() == "deepseek-chat"

    def test_default_base_url(self):
        assert DeepSeekProvider().base_url == "https://api.deepseek.com"

    def test_not_configured_without_key(self):
        assert DeepSeekProvider().is_configured() is False

    def test_configured_with_key(self):
        assert DeepSeekProvider(api_key="sk-test").is_configured() is True

    def test_base_url_strips_slash(self):
        provider = DeepSeekProvider(api_key="k", base_url="https://api.deepseek.com/")
        assert provider.base_url == "https://api.deepseek.com"


class TestOpenAIProvider:
    def test_default_model(self):
        assert OpenAIProvider().get_model_name() == "gpt-4o-mini"

    def test_default_base_url(self):
        assert OpenAIProvider().base_url == "https://api.openai.com/v1"


class TestNotConfigured:
    @pytest.mark.asyncio
    async def test_generate_raises_not_configured(self):
        provider = DeepSeekProvider(api_key="")
        with pytest.raises(LLMNotConfiguredError) as exc:
            await provider.generate([{"role": "user", "content": "hi"}])
        assert exc.value.error_code == "LLM_NOT_CONFIGURED"


class TestGenerateSuccess:
    @pytest.mark.asyncio
    async def test_generate_returns_response(self, fake_client):
        FakeAsyncClient.response = FakeResponse(data={
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        })
        provider = DeepSeekProvider(api_key="sk-test")
        response = await provider.generate([{"role": "user", "content": "hi"}])
        assert response.content == "hello"
        assert response.model == "deepseek-chat"
        assert response.input_tokens == 3
        assert response.output_tokens == 2

    @pytest.mark.asyncio
    async def test_posts_to_chat_completions(self, fake_client):
        provider = DeepSeekProvider(api_key="sk-test")
        await provider.generate([{"role": "user", "content": "hi"}])
        assert FakeAsyncClient.last_payload["url"] == "https://api.deepseek.com/chat/completions"

    @pytest.mark.asyncio
    async def test_sends_bearer_header(self, fake_client):
        provider = DeepSeekProvider(api_key="sk-test")
        await provider.generate([{"role": "user", "content": "hi"}])
        assert FakeAsyncClient.last_payload["headers"]["Authorization"] == "Bearer sk-test"

    @pytest.mark.asyncio
    async def test_uses_model_override(self, fake_client):
        provider = DeepSeekProvider(api_key="sk-test")
        await provider.generate([{"role": "user", "content": "hi"}], model="deepseek-reasoner")
        assert FakeAsyncClient.last_payload["json"]["model"] == "deepseek-reasoner"

    @pytest.mark.asyncio
    async def test_sets_temperature_and_max_tokens(self, fake_client):
        provider = DeepSeekProvider(api_key="sk-test")
        await provider.generate([{"role": "user", "content": "hi"}], temperature=0.5, max_tokens=100)
        assert FakeAsyncClient.last_payload["json"]["temperature"] == 0.5
        assert FakeAsyncClient.last_payload["json"]["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_finish_reason_defaults_to_stop(self, fake_client):
        FakeAsyncClient.response = FakeResponse(data={
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "x"}, "finish_reason": None}],
            "usage": {},
        })
        provider = DeepSeekProvider(api_key="sk-test")
        response = await provider.generate([{"role": "user", "content": "hi"}])
        assert response.finish_reason == "stop"


class TestErrorMapping:
    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self, fake_client):
        FakeAsyncClient.response = FakeResponse(status_code=401, text="bad key")
        provider = DeepSeekProvider(api_key="bad")
        with pytest.raises(LLMAuthError):
            await provider.generate([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_403_raises_auth_error(self, fake_client):
        FakeAsyncClient.response = FakeResponse(status_code=403, text="forbidden")
        provider = DeepSeekProvider(api_key="bad")
        with pytest.raises(LLMAuthError):
            await provider.generate([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit(self, fake_client):
        FakeAsyncClient.response = FakeResponse(status_code=429, text="slow down")
        provider = DeepSeekProvider(api_key="k")
        with pytest.raises(LLMRateLimitError):
            await provider.generate([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_500_raises_provider_error(self, fake_client):
        FakeAsyncClient.response = FakeResponse(status_code=500, text="boom")
        provider = DeepSeekProvider(api_key="k")
        with pytest.raises(LLMProviderError):
            await provider.generate([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_invalid_json_raises_provider_error(self, fake_client):
        FakeAsyncClient.response = FakeResponse(data="not json", text="not json")
        provider = DeepSeekProvider(api_key="k")
        with pytest.raises(LLMProviderError):
            await provider.generate([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self, fake_client):
        FakeAsyncClient.error = httpx.TimeoutException("too slow")
        provider = DeepSeekProvider(api_key="k")
        with pytest.raises(LLMTimeoutError):
            await provider.generate([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_http_error_raises_provider_error(self, fake_client):
        FakeAsyncClient.error = httpx.HTTPError("network")
        provider = DeepSeekProvider(api_key="k")
        with pytest.raises(LLMProviderError):
            await provider.generate([{"role": "user", "content": "hi"}])


class TestDeepSeekProviderMore:
    @pytest.mark.asyncio
    async def test_sends_stop_parameter(self, fake_client):
        provider = DeepSeekProvider(api_key="sk-test")
        await provider.generate([{"role": "user", "content": "hi"}], stop=["END"])
        assert FakeAsyncClient.last_payload["json"]["stop"] == ["END"]

    @pytest.mark.asyncio
    async def test_sends_top_p_parameter(self, fake_client):
        provider = DeepSeekProvider(api_key="sk-test")
        await provider.generate([{"role": "user", "content": "hi"}], top_p=0.9)
        assert FakeAsyncClient.last_payload["json"]["top_p"] == 0.9

    def test_openai_provider_configured(self):
        assert OpenAIProvider(api_key="sk").is_configured() is True

    @pytest.mark.asyncio
    async def test_reasoner_model_override(self, fake_client):
        provider = DeepSeekProvider(api_key="sk-test")
        await provider.generate([{"role": "user", "content": "hi"}], model="deepseek-reasoner")
        assert FakeAsyncClient.last_payload["json"]["model"] == "deepseek-reasoner"

