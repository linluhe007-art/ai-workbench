"""Tests for the Phase Beta-LLM provider abstraction."""

import pytest

from app.config import Settings
from app.llm.factory import create_llm_provider, get_llm_config_info
from app.llm.models import LLMMessage, LLMResponse, LLMRole, normalize_messages
from app.llm.provider import LLMProvider, MockLLMProvider


class TestLLMRole:
    def test_system_role(self):
        assert LLMRole.SYSTEM.value == "system"

    def test_user_role(self):
        assert LLMRole.USER.value == "user"

    def test_assistant_role(self):
        assert LLMRole.ASSISTANT.value == "assistant"


class TestLLMMessage:
    def test_create_message(self):
        message = LLMMessage(role=LLMRole.USER, content="hello")
        assert message.content == "hello"

    def test_to_dict(self):
        message = LLMMessage(role=LLMRole.USER, content="hello")
        assert message.to_dict() == {"role": "user", "content": "hello"}

    def test_to_dict_with_name(self):
        message = LLMMessage(role=LLMRole.SYSTEM, content="hi", name="planner")
        data = message.to_dict()
        assert data["name"] == "planner"

    def test_from_dict(self):
        message = LLMMessage.from_dict({"role": "assistant", "content": "ok"})
        assert message.role == LLMRole.ASSISTANT
        assert message.content == "ok"

    def test_from_dict_invalid_role_keeps_string(self):
        message = LLMMessage.from_dict({"role": "custom", "content": "x"})
        assert message.role == "custom"


class TestLLMResponse:
    def test_defaults(self):
        response = LLMResponse(content="ok")
        assert response.model == ""
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.finish_reason == "stop"

    def test_to_dict(self):
        response = LLMResponse(content="ok", model="deepseek-chat", input_tokens=2, output_tokens=3)
        data = response.to_dict()
        assert data["model"] == "deepseek-chat"
        assert data["input_tokens"] == 2
        assert data["output_tokens"] == 3


class TestNormalizeMessages:
    def test_empty_list(self):
        assert normalize_messages([]) == []

    def test_preserves_messages(self):
        message = LLMMessage(role=LLMRole.USER, content="x")
        assert normalize_messages([message]) == [message]

    def test_converts_dicts(self):
        messages = normalize_messages([{"role": "user", "content": "x"}])
        assert messages[0].role == LLMRole.USER

    def test_rejects_bad_type(self):
        with pytest.raises(TypeError):
            normalize_messages([123])


class TestMockLLMProvider:
    @pytest.mark.asyncio
    async def test_generate_basic(self):
        provider = MockLLMProvider()
        response = await provider.generate([{"role": "user", "content": "hello"}])
        assert "hello" in response.content
        assert response.model == "mock-llm-v1"

    @pytest.mark.asyncio
    async def test_generate_with_messages(self):
        provider = MockLLMProvider()
        messages = [LLMMessage(role=LLMRole.USER, content="hi")]
        response = await provider.generate(messages)
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_model_override(self):
        provider = MockLLMProvider()
        response = await provider.generate([{"role": "user", "content": "x"}], model="custom")
        assert response.model == "custom"

    def test_get_model_name(self):
        assert MockLLMProvider(default_model="m").get_model_name() == "m"

    def test_is_configured(self):
        assert MockLLMProvider().is_configured() is True


class TestFactory:
    def _settings(self, **overrides):
        values = {"llm_provider": "mock", "llm_model": "test-model", "deepseek_api_key": "", "openai_api_key": ""}
        values.update(overrides)
        return Settings(_env_file=None, **values)

    def test_create_mock(self):
        provider = create_llm_provider(provider="mock", model="mock-1")
        assert isinstance(provider, MockLLMProvider)
        assert provider.get_model_name() == "mock-1"

    def test_create_deepseek(self):
        provider = create_llm_provider(provider="deepseek", api_key="sk-test", model="deepseek-chat", settings=self._settings())
        assert provider.get_model_name() == "deepseek-chat"
        assert provider.is_configured() is True

    def test_create_openai(self):
        provider = create_llm_provider(provider="openai", api_key="sk-test", model="gpt-4o-mini", settings=self._settings())
        assert provider.get_model_name() == "gpt-4o-mini"
        assert provider.is_configured() is True

    def test_unknown_provider_falls_back_to_mock(self):
        provider = create_llm_provider(provider="nope", settings=self._settings())
        assert isinstance(provider, MockLLMProvider)

    def test_config_info_mock(self):
        info = get_llm_config_info(settings=self._settings())
        assert info["provider"] == "mock"
        assert info["configured"] is True

    def test_config_info_deepseek_unconfigured(self):
        info = get_llm_config_info(settings=self._settings(llm_provider="deepseek"))
        assert info["provider"] == "deepseek"
        assert info["api_key_set"] is False
        assert info["configured"] is False


class TestLLMProviderMore:
    def test_llm_message_to_dict_omits_name_by_default(self):
        message = LLMMessage(role=LLMRole.USER, content="hi")
        assert "name" not in message.to_dict()

    def test_normalize_none_returns_empty(self):
        assert normalize_messages(None) == []

    @pytest.mark.asyncio
    async def test_mock_generate_empty_messages(self):
        response = await MockLLMProvider().generate([])
        assert response.content
        assert response.model == "mock-llm-v1"

    @pytest.mark.asyncio
    async def test_mock_generate_metadata_provider(self):
        response = await MockLLMProvider().generate([{"role": "user", "content": "x"}])
        assert response.metadata["provider"] == "mock"

    def test_config_info_openai(self):
        info = get_llm_config_info(settings=Settings(_env_file=None, llm_provider="openai", openai_model="gpt-4o-mini", openai_api_key="sk", deepseek_api_key=""))
        assert info["provider"] == "openai"
        assert info["api_key_set"] is True

