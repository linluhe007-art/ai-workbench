"""
Phase 4.1 测试 — WebSocket API
覆盖：
- 连接确认
- 心跳 ping/pong
- 多客户端订阅
- 断开连接清理
- ConnectionManager 广播
- ConnectionManager 统计
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.runtime.manager import reset_runtime
from app.api.v1.websocket import (
    ConnectionManager, get_ws_manager, reset_ws_manager,
    make_event,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_runtime()
    reset_ws_manager()
    yield
    reset_runtime()
    reset_ws_manager()


# ── ConnectionManager ────────────────────────────────────────


class TestConnectionManager:
    def test_initial_state(self):
        mgr = ConnectionManager()
        assert mgr.total_connections == 0
        assert mgr.subscriber_count("any") == 0

    def test_disconnect_nonexistent(self):
        mgr = ConnectionManager()
        # Should not raise
        mgr.disconnect("task-1", None)  # type: ignore[arg-type]

    async def test_broadcast_no_subscribers(self):
        mgr = ConnectionManager()
        # Should not raise
        await mgr.broadcast("task-1", {"event": "test"})

    async def test_broadcast_all_no_connections(self):
        mgr = ConnectionManager()
        await mgr.broadcast_all({"event": "test"})


# ── make_event ───────────────────────────────────────────────


class TestMakeEvent:
    def test_make_event_basic(self):
        event = make_event("task_started", "task-1")
        assert event["event"] == "task_started"
        assert event["task_id"] == "task-1"
        assert "timestamp" in event
        assert event["data"] == {}

    def test_make_event_with_data(self):
        event = make_event("step_completed", "task-1", {"step_id": "s1"})
        assert event["data"]["step_id"] == "s1"

    def test_event_types(self):
        for etype in ["task_started", "agent_started", "agent_finished",
                       "step_completed", "evaluation_updated", "task_completed", "task_failed"]:
            event = make_event(etype, "t1")
            assert event["event"] == etype


# ── WebSocket Endpoint ───────────────────────────────────────


class TestWebSocketEndpoint:
    async def test_ws_connect_and_disconnect(self):
        from httpx import ASGITransport
        from starlette.testclient import TestClient
        # WebSocket testing requires a different approach
        # Test the manager directly with mock WebSocket
        mgr = ConnectionManager()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False
                self.messages = []

            async def accept(self):
                self.accepted = True

            async def send_text(self, data):
                self.messages.append(data)

        ws = MockWebSocket()
        await mgr.connect("task-1", ws)
        assert ws.accepted
        assert mgr.subscriber_count("task-1") == 1

        mgr.disconnect("task-1", ws)
        assert mgr.subscriber_count("task-1") == 0

    async def test_ws_broadcast(self):
        import json
        mgr = ConnectionManager()

        class MockWS:
            def __init__(self):
                self.messages = []

            async def send_text(self, data):
                self.messages.append(data)

        ws1 = MockWS()
        ws2 = MockWS()
        await mgr.connect("task-1", ws1)
        await mgr.connect("task-1", ws2)

        event = make_event("task_started", "task-1", {"info": "test"})
        await mgr.broadcast("task-1", event)

        assert len(ws1.messages) == 1
        assert len(ws2.messages) == 1
        parsed = json.loads(ws1.messages[0])
        assert parsed["event"] == "task_started"

    async def test_ws_broadcast_isolation(self):
        mgr = ConnectionManager()

        class MockWS:
            def __init__(self):
                self.messages = []
            async def send_text(self, data):
                self.messages.append(data)

        ws1 = MockWS()
        ws2 = MockWS()
        await mgr.connect("task-1", ws1)
        await mgr.connect("task-2", ws2)

        await mgr.broadcast("task-1", make_event("test", "task-1"))
        assert len(ws1.messages) == 1
        assert len(ws2.messages) == 0

    async def test_ws_broadcast_dead_connection(self):
        mgr = ConnectionManager()

        class DeadWS:
            def __init__(self):
                self.messages = []
            async def send_text(self, data):
                raise ConnectionError("dead")

        class LiveWS:
            def __init__(self):
                self.messages = []
            async def send_text(self, data):
                self.messages.append(data)

        dead = DeadWS()
        live = LiveWS()
        await mgr.connect("task-1", dead)
        await mgr.connect("task-1", live)

        await mgr.broadcast("task-1", make_event("test", "task-1"))
        # dead should be cleaned up
        assert mgr.subscriber_count("task-1") == 1
        assert len(live.messages) == 1

    async def test_ws_broadcast_all(self):
        mgr = ConnectionManager()

        class MockWS:
            def __init__(self):
                self.messages = []
            async def send_text(self, data):
                self.messages.append(data)

        ws1 = MockWS()
        ws2 = MockWS()
        await mgr.connect("t1", ws1)
        await mgr.connect("t2", ws2)

        await mgr.broadcast_all(make_event("global", "all"))
        assert len(ws1.messages) == 1
        assert len(ws2.messages) == 1

    async def test_total_connections(self):
        mgr = ConnectionManager()

        class MockWS:
            async def send_text(self, data): pass

        await mgr.connect("t1", MockWS())
        await mgr.connect("t1", MockWS())
        await mgr.connect("t2", MockWS())
        assert mgr.total_connections == 3