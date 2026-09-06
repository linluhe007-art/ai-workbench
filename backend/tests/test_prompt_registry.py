"""Phase 5.11 tests - Prompt Registry System"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.prompts.models import PromptTemplate
from app.prompts.registry import PromptRegistry, get_prompt_registry
from app.prompts.manager import PromptManager, get_prompt_manager
from app.main import app


# ========== PromptTemplate ==========

class TestPromptTemplate:
    def test_default(self):
        t = PromptTemplate(name="test", content="Hello")
        assert t.name == "test"
        assert t.version == 1

    def test_to_dict(self):
        t = PromptTemplate(name="greeting", content="Hi {{name}}", variables=["name"], description="Greet")
        d = t.to_dict()
        assert d["name"] == "greeting"
        assert d["variables"] == ["name"]

    def test_render(self):
        t = PromptTemplate(name="test", content="Hello {{user}}", variables=["user"])
        result = t.render(user="World")
        assert result == "Hello World"

    def test_render_multiple_vars(self):
        t = PromptTemplate(name="test", content="{{greeting}} {{name}}", variables=["greeting", "name"])
        result = t.render(greeting="Hi", name="Alice")
        assert result == "Hi Alice"

    def test_render_missing_var(self):
        t = PromptTemplate(name="test", content="Hello {{name}}", variables=["name"])
        result = t.render()
        assert result == "Hello "

    def test_active_default(self):
        t = PromptTemplate(name="test", content="x")
        assert t.active is True

    def test_unique_ids(self):
        t1 = PromptTemplate(name="a", content="x")
        t2 = PromptTemplate(name="b", content="y")
        assert t1.id != t2.id

# ========== PromptRegistry ==========

class TestPromptRegistry:
    def test_create(self):
        r = PromptRegistry()
        t = r.create("greeting", "Hello {{name}}", ["name"])
        assert t.name == "greeting"
        assert t.version == 1
        assert t.active is True

    def test_create_new_version(self):
        r = PromptRegistry()
        r.create("greeting", "v1", ["x"])
        t2 = r.create("greeting", "v2", ["x"])
        assert t2.version == 2
        assert t2.active is True
        # Old version should be deactivated
        t1 = r.get("greeting", version=1)
        assert t1.active is False

    def test_get_active(self):
        r = PromptRegistry()
        r.create("greeting", "Hello {{name}}", ["name"])
        t = r.get_active("greeting")
        assert t is not None
        assert t.version == 1

    def test_get_nonexistent(self):
        r = PromptRegistry()
        assert r.get("nonexistent") is None
        assert r.get_active("nonexistent") is None

    def test_list_all(self):
        r = PromptRegistry()
        r.create("p1", "content1")
        r.create("p2", "content2")
        all_prompts = r.list_all()
        assert len(all_prompts) >= 2

    def test_list_names(self):
        r = PromptRegistry()
        r.create("alpha", "a")
        r.create("beta", "b")
        names = r.list_names()
        assert "alpha" in names
        assert "beta" in names

    def test_activate_version(self):
        r = PromptRegistry()
        r.create("greeting", "v1")
        r.create("greeting", "v2")
        ok = r.activate_version("greeting", 1)
        assert ok is True
        t = r.get_active("greeting")
        assert t.version == 1

    def test_activate_invalid_version(self):
        r = PromptRegistry()
        r.create("greeting", "v1")
        ok = r.activate_version("greeting", 99)
        assert ok is False

    def test_activate_invalid_name(self):
        r = PromptRegistry()
        ok = r.activate_version("nonexistent", 1)
        assert ok is False

    def test_rollback(self):
        r = PromptRegistry()
        r.create("greeting", "v1")
        r.create("greeting", "v2")
        ok = r.rollback("greeting")
        assert ok is True
        t = r.get_active("greeting")
        assert t.version == 1

    def test_rollback_v1_fails(self):
        r = PromptRegistry()
        r.create("greeting", "v1")
        ok = r.rollback("greeting")
        assert ok is False

    def test_render(self):
        r = PromptRegistry()
        r.create("greeting", "Hello {{name}}!", ["name"])
        result = r.render("greeting", name="World")
        assert result == "Hello World!"

    def test_render_nonexistent(self):
        r = PromptRegistry()
        result = r.render("nonexistent")
        assert result == ""

    def test_singleton(self):
        r1 = get_prompt_registry()
        r2 = get_prompt_registry()
        assert r1 is r2

    def test_multiple_versions_in_list(self):
        r = PromptRegistry()
        r.create("test", "v1")
        r.create("test", "v2")
        r.create("test", "v3")
        all_p = r.list_all()
        versions = [p["version"] for p in all_p if p["name"] == "test"]
        assert len(versions) == 3

# ========== PromptManager ==========

class TestPromptManager:
    def test_create_prompt(self):
        m = PromptManager()
        p = m.create_prompt("test", "Hello {{x}}", ["x"], "desc")
        assert p["name"] == "test"
        assert p["version"] == 1

    def test_get_prompt(self):
        m = PromptManager()
        m.create_prompt("test", "content")
        p = m.get_prompt("test")
        assert p is not None

    def test_get_nonexistent(self):
        m = PromptManager()
        assert m.get_prompt("nonexistent") is None

    def test_list_prompts(self):
        m = PromptManager()
        m.create_prompt("p1", "c1")
        m.create_prompt("p2", "c2")
        prompts = m.list_prompts()
        assert len(prompts) >= 2

    def test_activate_version(self):
        m = PromptManager()
        m.create_prompt("test", "v1")
        m.create_prompt("test", "v2")
        m.activate_version("test", 1)
        p = m.get_prompt("test")
        assert p["version"] == 1

    def test_rollback(self):
        m = PromptManager()
        m.create_prompt("test", "v1")
        m.create_prompt("test", "v2")
        ok = m.rollback("test")
        assert ok is True

    def test_render(self):
        m = PromptManager()
        m.create_prompt("test", "Hi {{user}}", ["user"])
        result = m.render("test", user="Bob")
        assert result == "Hi Bob"

    def test_singleton(self):
        m1 = get_prompt_manager()
        m2 = get_prompt_manager()
        assert m1 is m2


# ========== API Tests ==========

@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestPromptAPI:
    @pytest.mark.asyncio
    async def test_create_prompt(self, client):
        resp = await client.post("/api/v1/prompts", json={
            "name": "test-prompt", "content": "Hello {{name}}", "variables": ["name"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["prompt"]["name"] == "test-prompt"

    @pytest.mark.asyncio
    async def test_list_prompts(self, client):
        resp = await client.get("/api/v1/prompts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "prompts" in data

    @pytest.mark.asyncio
    async def test_get_prompt(self, client):
        await client.post("/api/v1/prompts", json={"name": "get-test", "content": "test"})
        resp = await client.get("/api/v1/prompts/get-test")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_nonexistent_prompt(self, client):
        resp = await client.get("/api/v1/prompts/nonexistent-xyz")
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_activate_version(self, client):
        await client.post("/api/v1/prompts", json={"name": "ver-test", "content": "v1"})
        await client.post("/api/v1/prompts", json={"name": "ver-test", "content": "v2"})
        resp = await client.post("/api/v1/prompts/ver-test/activate?version=1")
        data = resp.json()
        assert data["success"] is True

class TestPromptExtra:
    def test_render_no_variables(self):
        r = PromptRegistry()
        r.create("test", "Static text")
        result = r.render("test")
        assert result == "Static text"

    def test_version_increment(self):
        r = PromptRegistry()
        r.create("test", "v1")
        r.create("test", "v2")
        r.create("test", "v3")
        t = r.get_active("test")
        assert t.version == 3

    def test_content_preserved(self):
        r = PromptRegistry()
        r.create("test", "Original content with {{var}}", ["var"])
        t = r.get_active("test")
        assert "{{var}}" in t.content

    def test_description_field(self):
        r = PromptRegistry()
        r.create("test", "content", description="A test prompt")
        t = r.get_active("test")
        assert t.description == "A test prompt"

    def test_api_create_minimal(self, client):
        # client fixture already defined above
        ...
