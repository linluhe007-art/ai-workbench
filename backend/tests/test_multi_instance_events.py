"""Phase 4.19: Multi-instance event bridge tests."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.execution.event_bridge import EventBridge, BridgedEvent


class TestBridgedEvent:

    def test_create_event(self):
        e = BridgedEvent(
            event_id="ev1", source_instance_id="i1",
            event_type="task_started", task_id="t1", sequence=1,
            timestamp="2024-01-01T00:00:00", data={"key": "val"}
        )
        assert e.event_id == "ev1"
        assert e.source_instance_id == "i1"
        assert e.task_id == "t1"
        assert e.sequence == 1

    def test_to_dict(self):
        e = BridgedEvent(event_id="e1", source_instance_id="i1", event_type="test", task_id="t1", sequence=1, timestamp="ts")
        d = e.to_dict()
        assert d["event_id"] == "e1"
        assert d["source_instance_id"] == "i1"
        assert d["event_type"] == "test"

    def test_from_dict(self):
        d = {"event_id": "e1", "source_instance_id": "i1", "event_type": "test", "task_id": "t1", "sequence": 1, "timestamp": "ts"}
        e = BridgedEvent.from_dict(d)
        assert e.event_id == "e1"
        assert e.source_instance_id == "i1"

    def test_default_values(self):
        e = BridgedEvent(event_id="", source_instance_id="", event_type="", task_id="", sequence=0)
        assert e.data == {}


class TestEventBridge:

    def test_init(self):
        bridge = EventBridge("my-instance")
        assert bridge._instance_id == "my-instance"
        assert bridge._running is False

    def test_is_local(self):
        bridge = EventBridge("inst-a")
        assert bridge._is_local("inst-a")
        assert not bridge._is_local("inst-b")
        assert bridge._is_local("")  # empty source is local

    def test_is_duplicate(self):
        bridge = EventBridge("inst-a")
        assert not bridge._is_duplicate("ev1")
        assert bridge._is_duplicate("ev1")
        assert not bridge._is_duplicate("ev2")

    def test_duplicate_set_trimming(self):
        bridge = EventBridge("inst-a")
        bridge._max_seen = 10
        for i in range(20):
            bridge._is_duplicate(f"ev{i}")
        assert len(bridge._seen_events) <= 10

    @pytest.mark.asyncio
    async def test_bridge_local_event_no_bus(self):
        bridge = EventBridge("inst-a")
        await bridge.bridge_local_event("task_started", "t1")

    @pytest.mark.asyncio
    async def test_bridge_local_event_with_bus(self):
        bridge = EventBridge("inst-a")
        mock_bus = MagicMock()
        mock_bus.channel_for_task = MagicMock(return_value="workbench:task:t1")
        mock_bus.publish = AsyncMock(return_value=1)
        bridge.set_event_bus(mock_bus)
        await bridge.bridge_local_event("task_started", "t1", sequence=1)
        assert mock_bus.publish.called

    @pytest.mark.asyncio
    async def test_handle_remote_event_skips_own(self):
        bridge = EventBridge("inst-a")
        payload = {"event_type": "test", "data": {"source_instance_id": "inst-a", "event_id": "ev1"}}
        await bridge.handle_remote_event(payload)

    @pytest.mark.asyncio
    async def test_handle_remote_event_skips_duplicate(self):
        bridge = EventBridge("inst-a")
        payload = {"event_type": "test", "data": {"source_instance_id": "inst-b", "event_id": "ev1"}}
        await bridge.handle_remote_event(payload)
        await bridge.handle_remote_event(payload)  # second call should be skipped

    @pytest.mark.asyncio
    async def test_register_ws_callback(self):
        bridge = EventBridge("inst-a")
        called = []
        def cb(task_id, event):
            called.append(task_id)
        bridge.register_ws_callback("t1", cb)
        assert "t1" in bridge._ws_callbacks
        assert len(bridge._ws_callbacks["t1"]) == 1

    def test_unregister_ws_callback(self):
        bridge = EventBridge("inst-a")
        cb1 = lambda tid, ev: None
        cb2 = lambda tid, ev: None
        bridge.register_ws_callback("t1", cb1)
        bridge.register_ws_callback("t1", cb2)
        bridge.unregister_ws_callback("t1", cb1)
        assert len(bridge._ws_callbacks["t1"]) == 1
        bridge.unregister_ws_callback("t1", cb2)
        assert "t1" not in bridge._ws_callbacks

    @pytest.mark.asyncio
    async def test_handle_remote_event_dispatches_ws(self):
        bridge = EventBridge("inst-a")
        called = []
        async def cb(task_id, event):
            called.append(task_id)
        bridge.register_ws_callback("t1", cb)
        payload = {"event_type": "task_started", "data": {"source_instance_id": "inst-b", "event_id": "ev2", "task_id": "t1"}}
        await bridge.handle_remote_event(payload)
        assert "t1" in called

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe_task(self):
        bridge = EventBridge("inst-a")
        mock_bus = MagicMock()
        mock_bus.channel_for_task = MagicMock(return_value="workbench:task:t1")
        mock_bus._handlers = {}
        bridge.set_event_bus(mock_bus)
        await bridge.subscribe_task("t1")
        assert "workbench:task:t1" in mock_bus._handlers
        await bridge.unsubscribe_task("t1")


class TestEventBridgeDefaultInstance:

    def test_default_instance_id(self):
        bridge = EventBridge()
        assert bridge._instance_id == ""
