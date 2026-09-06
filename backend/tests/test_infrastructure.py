"""
Phase 4.16 tests - Distributed Runtime & Event Infrastructure.
Covers: RedisClient, DistributedEventBus, DistributedLock, LockManager,
DistributedStateManager, instance registry, pub/sub channels.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.redis_client import RedisClient
from app.infrastructure.event_bus import DistributedEventBus
from app.infrastructure.distributed_lock import DistributedLock, LockManager
from app.infrastructure.state_manager import DistributedStateManager


# =============================================================================
# Helpers - create mocked RedisClient
# =============================================================================

def _mock_redis_client() -> RedisClient:
    """Create a RedisClient with mocked internal client."""
    rc = RedisClient.__new__(RedisClient)
    rc._url = "redis://mock:6379/0"
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = 0
    mock_redis.keys.return_value = []
    mock_redis.publish.return_value = 1
    mock_redis.setnx.return_value = True
    mock_redis.hset.return_value = 1
    mock_redis.hgetall.return_value = {}
    mock_redis.hdel.return_value = 1
    mock_redis.sadd.return_value = 1
    mock_redis.smembers.return_value = set()
    mock_redis.lpush.return_value = 1
    mock_redis.rpop.return_value = None
    mock_redis.llen.return_value = 0
    mock_redis.incr.return_value = 1
    mock_redis.aclose = AsyncMock()
    rc._client = mock_redis
    return rc


# =============================================================================
# RedisClient Tests
# =============================================================================

class TestRedisClient:
    def test_redis_client_creation(self):
        rc = _mock_redis_client()
        assert rc._url == "redis://mock:6379/0"

    @pytest.mark.asyncio
    async def test_connect_ping(self):
        rc = _mock_redis_client()
        await rc.connect()
        rc._client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        rc = _mock_redis_client()
        await rc.disconnect()
        rc._client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_string(self):
        rc = _mock_redis_client()
        await rc.set("key1", "value1")
        rc._client.set.assert_called_with("key1", "value1")

    @pytest.mark.asyncio
    async def test_set_json(self):
        rc = _mock_redis_client()
        await rc.set("key1", {"a": 1})
        rc._client.set.assert_called_with("key1", '{"a": 1}')

    @pytest.mark.asyncio
    async def test_set_with_ttl(self):
        rc = _mock_redis_client()
        await rc.set("key1", "value1", ttl=60)
        rc._client.set.assert_called_with("key1", "value1", ex=60)

    @pytest.mark.asyncio
    async def test_get_returns_value(self):
        rc = _mock_redis_client()
        rc._client.get.return_value = "hello"
        val = await rc.get("key1")
        assert val == "hello"

    @pytest.mark.asyncio
    async def test_get_json_valid(self):
        rc = _mock_redis_client()
        rc._client.get.return_value = '{"x": 42}'
        val = await rc.get_json("key1")
        assert val == {"x": 42}

    @pytest.mark.asyncio
    async def test_get_json_invalid(self):
        rc = _mock_redis_client()
        rc._client.get.return_value = "plain text"
        val = await rc.get_json("key1")
        assert val == "plain text"

    @pytest.mark.asyncio
    async def test_get_json_none(self):
        rc = _mock_redis_client()
        rc._client.get.return_value = None
        val = await rc.get_json("key1")
        assert val is None

    @pytest.mark.asyncio
    async def test_delete_keys(self):
        rc = _mock_redis_client()
        rc._client.delete.return_value = 2
        count = await rc.delete("k1", "k2")
        assert count == 2
        rc._client.delete.assert_called_with("k1", "k2")

    @pytest.mark.asyncio
    async def test_delete_no_keys(self):
        rc = _mock_redis_client()
        count = await rc.delete()
        assert count == 0

    @pytest.mark.asyncio
    async def test_exists_true(self):
        rc = _mock_redis_client()
        rc._client.exists.return_value = 1
        assert await rc.exists("key1") is True

    @pytest.mark.asyncio
    async def test_exists_false(self):
        rc = _mock_redis_client()
        rc._client.exists.return_value = 0
        assert await rc.exists("key1") is False

    @pytest.mark.asyncio
    async def test_keys_pattern(self):
        rc = _mock_redis_client()
        rc._client.keys.return_value = ["k1", "k2"]
        keys = await rc.keys("workbench:*")
        assert keys == ["k1", "k2"]

    @pytest.mark.asyncio
    async def test_hash_operations(self):
        rc = _mock_redis_client()
        rc._client.hset.return_value = 3
        result = await rc.hset("hash1", {"a": "1", "b": "2"})
        assert result == 3

    @pytest.mark.asyncio
    async def test_hgetall(self):
        rc = _mock_redis_client()
        rc._client.hgetall.return_value = {"status": "running", "attempt": "1"}
        data = await rc.hgetall("hash1")
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_set_operations(self):
        rc = _mock_redis_client()
        rc._client.sadd.return_value = 2
        result = await rc.sadd("set1", "a", "b")
        assert result == 2

    @pytest.mark.asyncio
    async def test_smembers(self):
        rc = _mock_redis_client()
        rc._client.smembers.return_value = {"a", "b"}
        result = await rc.smembers("set1")
        assert result == {"a", "b"}

    @pytest.mark.asyncio
    async def test_list_operations(self):
        rc = _mock_redis_client()
        rc._client.lpush.return_value = 3
        result = await rc.lpush("list1", "x", "y", "z")
        assert result == 3

    @pytest.mark.asyncio
    async def test_rpop(self):
        rc = _mock_redis_client()
        rc._client.rpop.return_value = "item"
        val = await rc.rpop("list1")
        assert val == "item"

    @pytest.mark.asyncio
    async def test_lrange(self):
        rc = _mock_redis_client()
        rc._client.lrange.return_value = ["a", "b"]
        result = await rc.lrange("list1", 0, 1)
        assert result == ["a", "b"]

    @pytest.mark.asyncio
    async def test_incr(self):
        rc = _mock_redis_client()
        rc._client.incr.return_value = 42
        val = await rc.incr("counter1")
        assert val == 42

    @pytest.mark.asyncio
    async def test_setnx_success(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = True
        result = await rc.setnx("key", "val")
        assert result is True

    @pytest.mark.asyncio
    async def test_setnx_with_ttl(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = True
        result = await rc.setnx("key", "val", ttl=30)
        assert result is True
        rc._client.set.assert_called_with("key", "val", nx=True, ex=30)

    @pytest.mark.asyncio
    async def test_ping_success(self):
        rc = _mock_redis_client()
        rc._client.ping.return_value = True
        assert await rc.ping() is True

    @pytest.mark.asyncio
    async def test_ping_failure(self):
        rc = _mock_redis_client()
        rc._client.ping.side_effect = Exception("no connection")
        assert await rc.ping() is False


# =============================================================================
# DistributedEventBus Tests
# =============================================================================

class TestDistributedEventBus:
    def test_channel_naming(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "inst-1")
        assert bus.channel_for_task("task-1") == "workbench:task:task-1"
        assert bus.channel_for_agent("agent-1") == "workbench:agent:agent-1"
        assert bus.channel_for_instance() == "workbench:instance:inst-1"
        assert bus.SYSTEM_CHANNEL == "workbench:system"

    @pytest.mark.asyncio
    async def test_publish_task_event(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "inst-1")
        count = await bus.publish_task_event("task-1", "task_started", {"attempt": 1})
        assert count == 1
        rc._client.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_agent_event(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "inst-1")
        await bus.publish_agent_event("agent-1", "agent_running")
        rc._client.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_system_event(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "inst-1")
        await bus.publish_system_event("instance_join", {"instances": 3})
        rc._client.publish.assert_called_once()

    def test_subscribe_handler(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "inst-1")
        received = []

        def handler(payload):
            received.append(payload)

        bus.subscribe("workbench:task:task-1", handler)
        assert len(bus._handlers["workbench:task:task-1"]) == 1

    def test_unsubscribe_handler(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "inst-1")
        handler = lambda p: None  # noqa: E731
        bus.subscribe("ch1", handler)
        bus.unsubscribe("ch1", handler)
        assert len(bus._handlers["ch1"]) == 0

    def test_multiple_subscribers(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "inst-1")
        bus.subscribe("ch1", lambda p: None)
        bus.subscribe("ch1", lambda p: None)
        assert len(bus._handlers["ch1"]) == 2


# =============================================================================
# DistributedLock Tests
# =============================================================================

class TestDistributedLock:
    def test_lock_name_and_key(self):
        rc = _mock_redis_client()
        lock = DistributedLock(rc, "task-lock", ttl_seconds=60)
        assert lock._name == "task-lock"
        assert lock._key == "lock:task-lock"
        assert lock._ttl == 60

    @pytest.mark.asyncio
    async def test_acquire_success(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = True
        lock = DistributedLock(rc, "test-lock")
        result = await lock.acquire(timeout=0)
        assert result is True
        assert lock.is_locked is True

    @pytest.mark.asyncio
    async def test_acquire_failure(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = False
        lock = DistributedLock(rc, "contested-lock")
        result = await lock.acquire(timeout=0)
        assert result is False
        assert lock.is_locked is False

    @pytest.mark.asyncio
    async def test_release_success(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = True
        rc._client.eval.return_value = 1
        lock = DistributedLock(rc, "test-lock")
        await lock.acquire(timeout=0)
        result = await lock.release()
        assert result is True
        assert lock.is_locked is False

    @pytest.mark.asyncio
    async def test_release_without_acquire(self):
        rc = _mock_redis_client()
        lock = DistributedLock(rc, "test-lock")
        result = await lock.release()
        assert result is False

    @pytest.mark.asyncio
    async def test_extend_success(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = True
        rc._client.eval.return_value = 1
        lock = DistributedLock(rc, "test-lock")
        await lock.acquire(timeout=0)
        result = await lock.extend(120)
        assert result is True

    @pytest.mark.asyncio
    async def test_extend_without_acquire(self):
        rc = _mock_redis_client()
        lock = DistributedLock(rc, "test-lock")
        result = await lock.extend(120)
        assert result is False

    @pytest.mark.asyncio
    async def test_context_manager_acquire(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = True
        rc._client.eval.return_value = 1
        lock = DistributedLock(rc, "ctx-lock")
        async with lock:
            assert lock.is_locked is True
        assert lock.is_locked is False


class TestLockManager:
    @pytest.mark.asyncio
    async def test_get_lock_returns_same_instance(self):
        rc = _mock_redis_client()
        mgr = LockManager(rc)
        lock1 = mgr.get_lock("lock-a")
        lock2 = mgr.get_lock("lock-a")
        assert lock1 is lock2

    @pytest.mark.asyncio
    async def test_get_lock_different_names(self):
        rc = _mock_redis_client()
        mgr = LockManager(rc)
        lock1 = mgr.get_lock("lock-a")
        lock2 = mgr.get_lock("lock-b")
        assert lock1 is not lock2

    @pytest.mark.asyncio
    async def test_lock_context_manager_success(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = True
        rc._client.eval.return_value = 1
        mgr = LockManager(rc)
        async with mgr.lock("critical-section", ttl_seconds=10, timeout=0):
            pass  # should not raise


# =============================================================================
# DistributedStateManager Tests
# =============================================================================

class TestDistributedStateManager:
    def test_task_key(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        assert sm._task_key("task-1") == "workbench:state:task:task-1"

    def test_agent_key(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        assert sm._agent_key("agent-1") == "workbench:state:agent:agent-1"

    @pytest.mark.asyncio
    async def test_save_task_state(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.save_task_state("task-1", {"status": "running", "attempt": "2"})
        rc._client.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_task_state(self):
        rc = _mock_redis_client()
        rc._client.hgetall.return_value = {"status": "completed", "attempt": "1"}
        sm = DistributedStateManager(rc)
        state = await sm.get_task_state("task-1")
        assert state["status"] == "completed"

    @pytest.mark.asyncio
    async def test_delete_task_state(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.delete_task_state("task-1")
        rc._client.delete.assert_called_with("workbench:state:task:task-1")

    @pytest.mark.asyncio
    async def test_update_task_field(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.update_task_field("task-1", "status", "completed")
        rc._client.hset.assert_called_with("workbench:state:task:task-1", {"status": "completed"})

    @pytest.mark.asyncio
    async def test_save_agent_state(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.save_agent_state("agent-1", {"state": "RUNNING"})
        rc._client.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_agent_state(self):
        rc = _mock_redis_client()
        rc._client.hgetall.return_value = {"state": "IDLE"}
        sm = DistributedStateManager(rc)
        state = await sm.get_agent_state("agent-1")
        assert state["state"] == "IDLE"

    @pytest.mark.asyncio
    async def test_delete_agent_state(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.delete_agent_state("agent-1")
        rc._client.delete.assert_called_with("workbench:state:agent:agent-1")

    @pytest.mark.asyncio
    async def test_register_instance(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.register_instance("inst-1", {"host": "node1"})
        rc._client.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.heartbeat("inst-1")
        rc._client.set.assert_called_with("workbench:state:heartbeat:inst-1", "alive", ex=30)

    @pytest.mark.asyncio
    async def test_get_active_instances(self):
        rc = _mock_redis_client()
        rc._client.keys.return_value = [
            "workbench:state:heartbeat:inst-1",
            "workbench:state:heartbeat:inst-2",
        ]
        sm = DistributedStateManager(rc)
        instances = await sm.get_active_instances()
        assert "inst-1" in instances
        assert "inst-2" in instances

    @pytest.mark.asyncio
    async def test_get_active_instances_empty(self):
        rc = _mock_redis_client()
        rc._client.keys.return_value = []
        sm = DistributedStateManager(rc)
        instances = await sm.get_active_instances()
        assert instances == []

    @pytest.mark.asyncio
    async def test_deregister_instance(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.deregister_instance("inst-1")
        assert rc._client.hdel.called
        assert rc._client.delete.called

    @pytest.mark.asyncio
    async def test_set_global(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.set_global("config:version", "1.0")
        rc._client.set.assert_called_with("workbench:state:global:config:version", "1.0", ttl=0)

    @pytest.mark.asyncio
    async def test_set_global_with_ttl(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.set_global("session:abc", {"user": "admin"}, ttl=3600)
        rc._client.set.assert_called_with("workbench:state:global:session:abc", '{"user": "admin"}', ex=3600)

    @pytest.mark.asyncio
    async def test_get_global(self):
        rc = _mock_redis_client()
        rc._client.get.return_value = '{"version": "2.0"}'
        sm = DistributedStateManager(rc)
        val = await sm.get_global("config:version")
        assert val == {"version": "2.0"}

    @pytest.mark.asyncio
    async def test_delete_global(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.delete_global("config:old")
        rc._client.delete.assert_called_with("workbench:state:global:config:old")

    @pytest.mark.asyncio
    async def test_incr_counter(self):
        rc = _mock_redis_client()
        rc._client.incr.return_value = 5
        sm = DistributedStateManager(rc)
        val = await sm.incr_counter("task_count")
        assert val == 5
        rc._client.incr.assert_called_with("workbench:state:counter:task_count")


# =============================================================================
# Integration Tests - Event Bus with State Manager
# =============================================================================

class TestIntegrationEventState:
    @pytest.mark.asyncio
    async def test_event_bus_publish_updates_state(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "inst-test")
        sm = DistributedStateManager(rc)

        # Simulate task lifecycle
        await bus.publish_task_event("task-1", "task_started")
        rc._client.publish.assert_called_once()

        await sm.save_task_state("task-1", {"status": "running"})
        rc._client.hset.assert_called()

    @pytest.mark.asyncio
    async def test_lock_protects_critical_section(self):
        rc = _mock_redis_client()
        rc._client.set.return_value = True
        rc._client.eval.return_value = 1

        lock = DistributedLock(rc, "global-update")
        acquired = await lock.acquire(timeout=0)
        assert acquired is True

        # Protected operation
        sm = DistributedStateManager(rc)
        await sm.incr_counter("protected_counter")
        rc._client.incr.assert_called_once()

        await lock.release()
        assert lock.is_locked is False

    @pytest.mark.asyncio
    async def test_multiple_instance_registry(self):
        rc = _mock_redis_client()
        rc._client.keys.return_value = [
            "workbench:state:heartbeat:inst-1",
            "workbench:state:heartbeat:inst-2",
            "workbench:state:heartbeat:inst-3",
        ]
        sm = DistributedStateManager(rc)
        instances = await sm.get_active_instances()
        assert len(instances) == 3
# =============================================================================
# Additional Integration & Edge Case Tests
# =============================================================================

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_state_manager_non_string_values_converted(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.save_task_state("t1", {"attempt": 3, "active": True, "score": 9.5})
        call_args = rc._client.hset.call_args[0]
        mapping = call_args[1]
        assert mapping["attempt"] == "3"
        assert mapping["active"] == "True"
        assert mapping["score"] == "9.5"

    @pytest.mark.asyncio
    async def test_event_bus_payload_structure(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "node-alpha")
        await bus.publish("test:channel", "custom_event", {"key": "value"})
        call_args = rc._client.publish.call_args[0]
        channel = call_args[0]
        message = call_args[1]
        assert channel == "test:channel"
        payload = json.loads(message)
        assert payload["event_type"] == "custom_event"
        assert payload["source_instance"] == "node-alpha"
        assert payload["data"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_event_bus_publish_without_data(self):
        rc = _mock_redis_client()
        bus = DistributedEventBus(rc, "node-1")
        await bus.publish("ch", "ping")
        call_args = rc._client.publish.call_args[0]
        message = json.loads(call_args[1])
        assert message["data"] == {}

    @pytest.mark.asyncio
    async def test_lock_ttl_default(self):
        rc = _mock_redis_client()
        lock = DistributedLock(rc, "default-ttl")
        assert lock._ttl == 30

    @pytest.mark.asyncio
    async def test_lock_ttl_custom(self):
        rc = _mock_redis_client()
        lock = DistributedLock(rc, "custom-ttl", ttl_seconds=120)
        assert lock._ttl == 120

    @pytest.mark.asyncio
    async def test_state_manager_heartbeat_custom_ttl(self):
        rc = _mock_redis_client()
        sm = DistributedStateManager(rc)
        await sm.heartbeat("inst-99", ttl=60)
        rc._client.set.assert_called_with("workbench:state:heartbeat:inst-99", "alive", ex=60)