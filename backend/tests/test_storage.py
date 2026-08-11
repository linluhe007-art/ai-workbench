"""
Phase 3.19 测试 — Storage Backend
覆盖：
- MemoryStorage CRUD
- FileStorage CRUD
- batch operations
- prefix listing
- exists / count
"""

import json
import os
import pytest
import tempfile

from app.storage.memory import MemoryStorage
from app.storage.file import FileStorage


# ── MemoryStorage ────────────────────────────────────────────


class TestMemoryStorage:
    async def test_save_and_get(self):
        store = MemoryStorage()
        await store.save("key1", {"name": "test"})
        result = await store.get("key1")
        assert result == {"name": "test"}

    async def test_get_nonexistent(self):
        store = MemoryStorage()
        result = await store.get("missing")
        assert result is None

    async def test_overwrite(self):
        store = MemoryStorage()
        await store.save("key1", "v1")
        await store.save("key1", "v2")
        result = await store.get("key1")
        assert result == "v2"

    async def test_delete_existing(self):
        store = MemoryStorage()
        await store.save("key1", "v1")
        deleted = await store.delete("key1")
        assert deleted is True
        assert (await store.get("key1")) is None

    async def test_delete_nonexistent(self):
        store = MemoryStorage()
        deleted = await store.delete("missing")
        assert deleted is False

    async def test_list_keys_empty(self):
        store = MemoryStorage()
        keys = await store.list_keys()
        assert keys == []

    async def test_list_keys_no_prefix(self):
        store = MemoryStorage()
        await store.save("a:1", 1)
        await store.save("b:2", 2)
        keys = await store.list_keys()
        assert set(keys) == {"a:1", "b:2"}

    async def test_list_keys_with_prefix(self):
        store = MemoryStorage()
        await store.save("agent:a1", 1)
        await store.save("agent:a2", 2)
        await store.save("exec:t1", 3)
        keys = await store.list_keys("agent:")
        assert set(keys) == {"agent:a1", "agent:a2"}

    async def test_exists(self):
        store = MemoryStorage()
        assert (await store.exists("key1")) is False
        await store.save("key1", "v1")
        assert (await store.exists("key1")) is True

    async def test_count(self):
        store = MemoryStorage()
        await store.save("a:1", 1)
        await store.save("a:2", 2)
        await store.save("b:1", 3)
        assert (await store.count()) == 3
        assert (await store.count("a:")) == 2

    async def test_save_many(self):
        store = MemoryStorage()
        count = await store.save_many({"k1": 1, "k2": 2, "k3": 3})
        assert count == 3
        assert (await store.get("k1")) == 1

    async def test_get_many(self):
        store = MemoryStorage()
        await store.save("k1", 10)
        await store.save("k2", 20)
        result = await store.get_many(["k1", "k2", "k3"])
        assert result == {"k1": 10, "k2": 20}

    async def test_deep_copy_isolation(self):
        store = MemoryStorage()
        data = {"nested": [1, 2]}
        await store.save("key", data)
        data["nested"].append(3)
        result = await store.get("key")
        assert result == {"nested": [1, 2]}

    async def test_clear(self):
        store = MemoryStorage()
        await store.save("k1", 1)
        await store.save("k2", 2)
        store.clear()
        assert (await store.count()) == 0


# ── FileStorage ──────────────────────────────────────────────


class TestFileStorage:
    @pytest.fixture
    def tmp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            yield d

    async def test_save_and_get(self, tmp_dir):
        store = FileStorage(tmp_dir)
        await store.save("test:key", {"value": 42})
        result = await store.get("test:key")
        assert result == {"value": 42}

    async def test_get_nonexistent(self, tmp_dir):
        store = FileStorage(tmp_dir)
        result = await store.get("missing:key")
        assert result is None

    async def test_delete_existing(self, tmp_dir):
        store = FileStorage(tmp_dir)
        await store.save("k:v", "data")
        deleted = await store.delete("k:v")
        assert deleted is True
        assert (await store.get("k:v")) is None

    async def test_delete_nonexistent(self, tmp_dir):
        store = FileStorage(tmp_dir)
        deleted = await store.delete("no:such")
        assert deleted is False

    async def test_list_keys_with_prefix(self, tmp_dir):
        store = FileStorage(tmp_dir)
        await store.save("agent:a1", 1)
        await store.save("agent:a2", 2)
        await store.save("exec:t1", 3)
        keys = await store.list_keys("agent:")
        assert len(keys) == 2

    async def test_exists(self, tmp_dir):
        store = FileStorage(tmp_dir)
        assert (await store.exists("k:v")) is False
        await store.save("k:v", 1)
        assert (await store.exists("k:v")) is True

    async def test_count(self, tmp_dir):
        store = FileStorage(tmp_dir)
        await store.save("a:1", 1)
        await store.save("a:2", 2)
        assert (await store.count()) == 2
        assert (await store.count("a:")) == 2

    async def test_overwrite(self, tmp_dir):
        store = FileStorage(tmp_dir)
        await store.save("k:v", "old")
        await store.save("k:v", "new")
        result = await store.get("k:v")
        assert result == "new"

    async def test_persistence_across_instances(self, tmp_dir):
        store1 = FileStorage(tmp_dir)
        await store1.save("persistent:key", {"data": 123})
        store2 = FileStorage(tmp_dir)
        result = await store2.get("persistent:key")
        assert result == {"data": 123}

    async def test_json_format(self, tmp_dir):
        store = FileStorage(tmp_dir)
        await store.save("test:fmt", [1, 2, 3])
        path = store._key_to_path("test:fmt")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["key"] == "test:fmt"
        assert data["value"] == [1, 2, 3]
        assert "saved_at" in data

    async def test_complex_key(self, tmp_dir):
        store = FileStorage(tmp_dir)
        await store.save("a:b:c", "deep")
        result = await store.get("a:b:c")
        assert result == "deep"