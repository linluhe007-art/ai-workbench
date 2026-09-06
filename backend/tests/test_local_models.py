"""Phase 5.9 tests - Local AI Model Support"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.models.provider import (
    ProviderType, ModelInfo, ModelResponse,
    BaseLLMProvider, OllamaProvider, LlamaCppProvider,
    OpenAICompatibleProvider, ProviderFactory,
)
from app.models.router import (
    ModelRouter, RoutingDecision, TaskCategory, PrivacyLevel, get_model_router,
)
from app.models.manager import (
    ModelManager, ModelConfig, get_model_manager,
)
from app.main import app


# ========== ProviderType ==========

class TestProviderType:
    def test_values(self):
        assert ProviderType.OLLAMA == "ollama"
        assert ProviderType.LLAMA_CPP == "llama_cpp"
        assert ProviderType.OPENAI_COMPATIBLE == "openai_compatible"


# ========== ModelInfo ==========

class TestModelInfo:
    def test_basic(self):
        m = ModelInfo(name="llama3", provider=ProviderType.OLLAMA, context_length=8192)
        assert m.name == "llama3"
        assert m.provider == ProviderType.OLLAMA
        assert m.context_length == 8192

    def test_to_dict(self):
        m = ModelInfo(name="gpt-4", provider=ProviderType.OPENAI_COMPATIBLE, size="large")
        d = m.to_dict()
        assert d["name"] == "gpt-4"
        assert d["provider"] == "openai_compatible"
        assert d["size"] == "large"


# ========== ModelResponse ==========

class TestModelResponse:
    def test_basic(self):
        r = ModelResponse(text="Hello", model="llama3")
        assert r.text == "Hello"
        assert r.model == "llama3"
        assert r.error == ""

    def test_to_dict(self):
        r = ModelResponse(text="Hi", model="m", usage={"tokens": 10})
        d = r.to_dict()
        assert d["text"] == "Hi"
        assert d["usage"]["tokens"] == 10

    def test_with_error(self):
        r = ModelResponse(text="", model="", error="Failed")
        d = r.to_dict()
        assert d["error"] == "Failed"

# ========== OllamaProvider ==========

class TestOllamaProvider:
    @pytest.mark.asyncio
    async def test_list_models(self):
        p = OllamaProvider()
        models = await p.list_models()
        assert len(models) >= 1
        assert models[0].provider == ProviderType.OLLAMA

    @pytest.mark.asyncio
    async def test_generate(self):
        p = OllamaProvider()
        resp = await p.generate("Hello world", model="llama3")
        assert "llama3" in resp.model
        assert len(resp.text) > 0

    @pytest.mark.asyncio
    async def test_test_connection(self):
        p = OllamaProvider()
        ok = await p.test_connection()
        assert ok is True


# ========== LlamaCppProvider ==========

class TestLlamaCppProvider:
    @pytest.mark.asyncio
    async def test_list_models(self):
        p = LlamaCppProvider()
        models = await p.list_models()
        assert len(models) >= 1
        assert models[0].provider == ProviderType.LLAMA_CPP

    @pytest.mark.asyncio
    async def test_generate(self):
        p = LlamaCppProvider()
        resp = await p.generate("Test prompt")
        assert "llama.cpp" in resp.text or "llama-cpp" in resp.model

    @pytest.mark.asyncio
    async def test_test_connection(self):
        p = LlamaCppProvider()
        ok = await p.test_connection()
        assert ok is True


# ========== OpenAICompatibleProvider ==========

class TestOpenAICompatibleProvider:
    @pytest.mark.asyncio
    async def test_list_models(self):
        p = OpenAICompatibleProvider()
        models = await p.list_models()
        assert len(models) >= 1

    @pytest.mark.asyncio
    async def test_generate(self):
        p = OpenAICompatibleProvider()
        resp = await p.generate("Test prompt", model="gpt-4o-mini")
        assert resp.text != ""

    @pytest.mark.asyncio
    async def test_test_connection(self):
        p = OpenAICompatibleProvider()
        ok = await p.test_connection()
        assert ok is True


# ========== ProviderFactory ==========

class TestProviderFactory:
    def test_create_ollama(self):
        p = ProviderFactory.create(ProviderType.OLLAMA)
        assert isinstance(p, OllamaProvider)

    def test_create_llama_cpp(self):
        p = ProviderFactory.create(ProviderType.LLAMA_CPP)
        assert isinstance(p, LlamaCppProvider)

    def test_create_openai(self):
        p = ProviderFactory.create(ProviderType.OPENAI_COMPATIBLE)
        assert isinstance(p, OpenAICompatibleProvider)

    def test_create_with_endpoint(self):
        p = ProviderFactory.create(ProviderType.OLLAMA, endpoint="http://custom:9999")
        assert p.endpoint == "http://custom:9999"

    def test_create_invalid(self):
        with pytest.raises(ValueError):
            ProviderFactory.create("invalid")

# ========== RoutingDecision ==========

class TestRoutingDecision:
    def test_basic(self):
        d = RoutingDecision(provider_type=ProviderType.OLLAMA, model_name="llama3", reason="test")
        assert d.provider_type == ProviderType.OLLAMA
        assert d.model_name == "llama3"

    def test_to_dict(self):
        d = RoutingDecision(
            provider_type=ProviderType.OPENAI_COMPATIBLE, model_name="gpt-4",
            reason="Default", privacy_level=PrivacyLevel.MEDIUM, estimated_cost="low",
        )
        dd = d.to_dict()
        assert dd["provider_type"] == "openai_compatible"
        assert dd["model_name"] == "gpt-4"
        assert dd["privacy_level"] == "medium"


# ========== ModelRouter ==========

class TestModelRouter:
    def test_route_coding(self):
        r = ModelRouter()
        r.set_provider(ProviderType.OLLAMA, OllamaProvider())
        d = r.route("coding")
        assert d.provider_type == ProviderType.OLLAMA
        assert d.model_name == "codellama"

    def test_route_chat(self):
        r = ModelRouter()
        d = r.route("chat")
        assert d.model_name == "llama3"

    def test_route_research(self):
        r = ModelRouter()
        d = r.route("research")
        assert d.model_name == "deepseek-v3"

    def test_route_writing(self):
        r = ModelRouter()
        d = r.route("writing")
        assert d.model_name == "gpt-4o-mini"

    def test_route_private(self):
        r = ModelRouter()
        d = r.route("private")
        assert d.privacy_level == PrivacyLevel.STRICT
        assert d.provider_type == ProviderType.OLLAMA

    def test_route_unknown_category(self):
        r = ModelRouter()
        d = r.route("unknown_task")
        assert d.model_name == "llama3"  # fallback

    def test_route_with_privacy_escalation(self):
        r = ModelRouter()
        # research normally uses openai, but high privacy escalates to local
        d = r.route("research", privacy_level=PrivacyLevel.HIGH)
        assert d.provider_type == ProviderType.OLLAMA

    def test_custom_route(self):
        r = ModelRouter()
        custom = RoutingDecision(provider_type=ProviderType.LLAMA_CPP, model_name="custom-model", reason="Override")
        r.add_custom_route("chat", custom)
        d = r.route("chat")
        assert d.model_name == "custom-model"

    def test_get_routing_table(self):
        r = ModelRouter()
        table = r.get_routing_table()
        assert isinstance(table, dict)
        assert "coding" in table

    @pytest.mark.asyncio
    async def test_generate(self):
        r = ModelRouter()
        r.set_provider(ProviderType.OLLAMA, OllamaProvider())
        result = await r.generate("coding", "Write a function")
        assert "routing" in result
        assert "response" in result

    def test_set_and_get_provider(self):
        r = ModelRouter()
        p = OllamaProvider(endpoint="http://test:1234")
        r.set_provider(ProviderType.OLLAMA, p)
        assert r.get_provider(ProviderType.OLLAMA) is p

    def test_get_nonexistent_provider(self):
        r = ModelRouter()
        assert r.get_provider(ProviderType.LLAMA_CPP) is None

    def test_singleton(self):
        r1 = get_model_router()
        r2 = get_model_router()
        assert r1 is r2

# ========== ModelConfig ==========

class TestModelConfig:
    def test_basic(self):
        c = ModelConfig(provider_type=ProviderType.OLLAMA, endpoint="http://localhost:11434")
        assert c.provider_type == ProviderType.OLLAMA
        assert c.enabled is True

    def test_to_dict(self):
        c = ModelConfig(provider_type=ProviderType.OPENAI_COMPATIBLE, endpoint="http://api.test", api_key="sk-test")
        d = c.to_dict()
        assert d["provider_type"] == "openai_compatible"
        assert d["api_key_set"] is True

    def test_to_dict_no_api_key(self):
        c = ModelConfig(provider_type=ProviderType.OLLAMA)
        d = c.to_dict()
        assert d["api_key_set"] is False


# ========== ModelManager ==========

class TestModelManager:
    def test_configure_provider(self):
        m = ModelManager()
        m.configure(ProviderType.OLLAMA, endpoint="http://test:11434")
        config = m.get_config(ProviderType.OLLAMA)
        assert config is not None
        assert config.endpoint == "http://test:11434"

    def test_get_nonexistent_config(self):
        m = ModelManager()
        assert m.get_config(ProviderType.LLAMA_CPP) is None

    def test_list_configs(self):
        m = ModelManager()
        m.configure(ProviderType.OLLAMA)
        m.configure(ProviderType.OPENAI_COMPATIBLE, api_key="sk-test")
        configs = m.list_configs()
        assert len(configs) >= 2

    @pytest.mark.asyncio
    async def test_discover_models(self):
        m = ModelManager()
        m.configure(ProviderType.OLLAMA)
        models = await m.discover_models(ProviderType.OLLAMA)
        assert len(models) >= 1

    @pytest.mark.asyncio
    async def test_test_provider(self):
        m = ModelManager()
        m.configure(ProviderType.OLLAMA)
        ok = await m.test_provider(ProviderType.OLLAMA)
        assert ok is True

    @pytest.mark.asyncio
    async def test_test_all_providers(self):
        m = ModelManager()
        m.configure(ProviderType.OLLAMA)
        m.configure(ProviderType.LLAMA_CPP)
        results = await m.test_all_providers()
        assert len(results) >= 1

    def test_get_all_available_models(self):
        m = ModelManager()
        models = m.get_all_available_models()
        assert len(models) >= 1
        for model in models:
            assert "name" in model
            assert "provider" in model

    def test_get_router(self):
        m = ModelManager()
        router = m.get_router()
        assert isinstance(router, ModelRouter)

    def test_singleton(self):
        m1 = get_model_manager()
        m2 = get_model_manager()
        assert m1 is m2

    @pytest.mark.asyncio
    async def test_discover_all_models(self):
        m = ModelManager()
        m.configure(ProviderType.OLLAMA)
        m.configure(ProviderType.OPENAI_COMPATIBLE)
        models = await m.discover_models()
        assert len(models) >= 2  # both providers

    @pytest.mark.asyncio
    async def test_test_nonexistent_provider(self):
        m = ModelManager()
        ok = await m.test_provider(ProviderType.LLAMA_CPP)
        assert ok is False  # not configured

# ========== API Tests ==========

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestModelsAPI:
    @pytest.mark.asyncio
    async def test_list_models_200(self, client):
        resp = await client.get("/api/v1/models")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_models_structure(self, client):
        resp = await client.get("/api/v1/models")
        data = resp.json()
        assert data["success"] is True
        assert "routing_table" in data
        assert "configs" in data
        assert "available_models" in data

    @pytest.mark.asyncio
    async def test_list_providers(self, client):
        resp = await client.get("/api/v1/models/providers")
        data = resp.json()
        assert data["success"] is True
        assert len(data["providers"]) == 3

    @pytest.mark.asyncio
    async def test_configure_ollama(self, client):
        resp = await client.post("/api/v1/models/configure", json={
            "provider_type": "ollama", "endpoint": "http://localhost:11434",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_configure_invalid(self, client):
        resp = await client.post("/api/v1/models/configure", json={
            "provider_type": "invalid",
        })
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_test_ollama(self, client):
        await client.post("/api/v1/models/configure", json={"provider_type": "ollama"})
        resp = await client.post("/api/v1/models/test", json={"provider_type": "ollama"})
        data = resp.json()
        assert data["success"] is True
        assert "connected" in data

    @pytest.mark.asyncio
    async def test_test_invalid(self, client):
        resp = await client.post("/api/v1/models/test", json={"provider_type": "invalid"})
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_generate_coding(self, client):
        resp = await client.post("/api/v1/models/generate", json={
            "task_category": "coding", "prompt": "Write hello world",
        })
        data = resp.json()
        assert data["success"] is True
        assert "routing" in data

    @pytest.mark.asyncio
    async def test_generate_with_privacy(self, client):
        resp = await client.post("/api/v1/models/generate", json={
            "task_category": "research", "prompt": "Test", "privacy_level": "high",
        })
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_generate_chat(self, client):
        resp = await client.post("/api/v1/models/generate", json={
            "task_category": "chat", "prompt": "Hello",
        })
        data = resp.json()
        assert data["success"] is True

class TestModelRouterEdgeCases:
    def test_route_privacy_medium_to_high(self):
        r = ModelRouter()
        d = r.route("writing", privacy_level=PrivacyLevel.HIGH)
        # Writing normally uses openai (medium privacy), high privacy escalates
        assert d.provider_type == ProviderType.OLLAMA
        assert d.privacy_level == PrivacyLevel.HIGH
