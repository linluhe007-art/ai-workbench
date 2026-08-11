"""
Phase 3.9.1 测试 — Agent Message Bus
覆盖：
- AgentMessage 创建与序列化
- MessageBus send/receive
- 多 Agent 消息隔离
- broadcast 广播
- 并发发送安全性
- AgentRuntime 集成
- BaseAgent.send_message / receive_messages
"""

import asyncio
import pytest

from app.agents.message import AgentMessage
from app.agents.message_bus import MessageBus
from app.agents.runtime import AgentRuntime, AgentState
from app.agents.mock_agent import MockAgent


# ─── helpers ───────────────────────────────────────────────

def _make_bus_with_agents(count: int = 3) -> tuple[MessageBus, list[MockAgent]]:
    bus = MessageBus()
    agents = []
    for i in range(count):
        agent = MockAgent(f"agent-{i}")
        bus.register_agent(agent.id)
        agents.append(agent)
    return bus, agents


def _make_runtime_with_bus(count: int = 3) -> tuple[AgentRuntime, MessageBus, list[MockAgent]]:
    runtime = AgentRuntime()
    bus = MessageBus()
    agents = []
    for i in range(count):
        agent = MockAgent(f"agent-{i}")
        runtime.register(agent)
        agents.append(agent)
    runtime.set_message_bus(bus)
    return runtime, bus, agents


# ═══════════════════════════════════════════════════════════
# AgentMessage 测试
# ═══════════════════════════════════════════════════════════


class TestAgentMessageCreation:
    """AgentMessage 创建与字段"""

    def test_create_with_defaults(self):
        msg = AgentMessage(sender="a", receiver="b", content={"key": "value"})

        assert msg.sender == "a"
        assert msg.receiver == "b"
        assert msg.content == {"key": "value"}
        assert msg.message_type == "data"
        assert msg.id  # auto-generated UUID
        assert msg.created_at is not None

    def test_create_with_custom_fields(self):
        msg = AgentMessage(
            sender="agent-1",
            receiver="agent-2",
            content={"action": "query"},
            message_type="request",
        )

        assert msg.message_type == "request"
        assert msg.sender == "agent-1"
        assert msg.receiver == "agent-2"

    def test_id_is_unique(self):
        msg1 = AgentMessage(sender="a", receiver="b", content={})
        msg2 = AgentMessage(sender="a", receiver="b", content={})

        assert msg1.id != msg2.id

    def test_msg_type_backward_compat(self):
        """msg_type 属性兼容旧代码"""
        msg = AgentMessage(sender="a", receiver="b", content={}, message_type="error")

        assert msg.msg_type == "error"

    def test_to_dict(self):
        msg = AgentMessage(
            sender="a", receiver="b", content={"x": 1}, message_type="data",
        )
        d = msg.to_dict()

        assert d["id"] == msg.id
        assert d["sender"] == "a"
        assert d["receiver"] == "b"
        assert d["message_type"] == "data"
        assert d["msg_type"] == "data"
        assert d["content"] == {"x": 1}
        assert "created_at" in d

    def test_default_content_is_empty_dict(self):
        msg = AgentMessage(sender="a", receiver="b")
        assert msg.content == {}


# ═══════════════════════════════════════════════════════════
# MessageBus 测试
# ═══════════════════════════════════════════════════════════


class TestMessageBusSendReceive:
    """基本 send/receive"""

    @pytest.mark.asyncio
    async def test_send_and_receive(self):
        bus = MessageBus()
        bus.register_agent("a")
        bus.register_agent("b")

        msg = AgentMessage(sender="a", receiver="b", content={"hello": "world"})
        await bus.send(msg)

        messages = await bus.receive("b")
        assert len(messages) == 1
        assert messages[0].content == {"hello": "world"}
        assert messages[0].sender == "a"

    @pytest.mark.asyncio
    async def test_receive_clears_queue(self):
        bus = MessageBus()
        bus.register_agent("a")
        bus.register_agent("b")

        await bus.send(AgentMessage(sender="a", receiver="b", content={}))
        await bus.receive("b")

        messages = await bus.receive("b")
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_receive_empty(self):
        bus = MessageBus()
        bus.register_agent("a")

        messages = await bus.receive("a")
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_auto_ensure_queue_on_send(self):
        """send 自动创建不存在的队列"""
        bus = MessageBus()

        msg = AgentMessage(sender="external", receiver="new-agent", content={})
        await bus.send(msg)

        messages = await bus.receive("new-agent")
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_multiple_messages_ordering(self):
        bus = MessageBus()
        bus.register_agent("sender")
        bus.register_agent("receiver")

        for i in range(5):
            await bus.send(AgentMessage(
                sender="sender", receiver="receiver", content={"i": i},
            ))

        messages = await bus.receive("receiver")
        assert len(messages) == 5
        assert [m.content["i"] for m in messages] == [0, 1, 2, 3, 4]


class TestMessageBusIsolation:
    """多 Agent 消息隔离"""

    @pytest.mark.asyncio
    async def test_agents_receive_own_messages_only(self):
        bus, agents = _make_bus_with_agents(3)

        await bus.send(AgentMessage(sender="agent-0", receiver="agent-1", content={"to": "1"}))
        await bus.send(AgentMessage(sender="agent-0", receiver="agent-2", content={"to": "2"}))

        msgs_1 = await bus.receive("agent-1")
        msgs_2 = await bus.receive("agent-2")
        msgs_0 = await bus.receive("agent-0")

        assert len(msgs_1) == 1 and msgs_1[0].content["to"] == "1"
        assert len(msgs_2) == 1 and msgs_2[0].content["to"] == "2"
        assert len(msgs_0) == 0

    @pytest.mark.asyncio
    async def test_no_cross_contamination(self):
        bus = MessageBus()
        bus.register_agent("a")
        bus.register_agent("b")

        for i in range(10):
            await bus.send(AgentMessage(sender="a", receiver="b", content={"i": i}))

        b_msgs = await bus.receive("b")
        a_msgs = await bus.receive("a")

        assert len(b_msgs) == 10
        assert len(a_msgs) == 0


class TestMessageBusBroadcast:
    """广播测试"""

    @pytest.mark.asyncio
    async def test_broadcast_to_all_others(self):
        bus, _ = _make_bus_with_agents(4)

        await bus.broadcast(sender="agent-0", content={"announcement": "hello"})

        for aid in ("agent-1", "agent-2", "agent-3"):
            msgs = await bus.receive(aid)
            assert len(msgs) == 1
            assert msgs[0].content == {"announcement": "hello"}
            assert msgs[0].sender == "agent-0"
            assert msgs[0].message_type == "broadcast"

    @pytest.mark.asyncio
    async def test_broadcast_excludes_sender(self):
        bus, _ = _make_bus_with_agents(3)

        await bus.broadcast(sender="agent-0", content={"data": "test"})

        sender_msgs = await bus.receive("agent-0")
        assert len(sender_msgs) == 0

    @pytest.mark.asyncio
    async def test_broadcast_empty_registry(self):
        bus = MessageBus()

        await bus.broadcast(sender="nobody", content={"x": 1})
        # Should not raise

    @pytest.mark.asyncio
    async def test_broadcast_to_single_agent(self):
        bus = MessageBus()
        bus.register_agent("a")
        bus.register_agent("b")

        await bus.broadcast(sender="a", content={"msg": "only to b"})

        b_msgs = await bus.receive("b")
        assert len(b_msgs) == 1
        assert b_msgs[0].content == {"msg": "only to b"}


class TestMessageBusConcurrency:
    """并发安全测试"""

    @pytest.mark.asyncio
    async def test_concurrent_sends(self):
        bus = MessageBus()
        bus.register_agent("sender")
        bus.register_agent("receiver")

        async def send_one(i: int):
            await bus.send(AgentMessage(
                sender="sender", receiver="receiver", content={"i": i},
            ))

        await asyncio.gather(*[send_one(i) for i in range(100)])

        messages = await bus.receive("receiver")
        assert len(messages) == 100

        received_indices = {m.content["i"] for m in messages}
        assert received_indices == set(range(100))

    @pytest.mark.asyncio
    async def test_concurrent_send_receive(self):
        bus = MessageBus()
        bus.register_agent("a")
        bus.register_agent("b")

        sent = []
        received = []

        async def sender():
            for i in range(20):
                await bus.send(AgentMessage(
                    sender="a", receiver="b", content={"i": i},
                ))
                sent.append(i)
                await asyncio.sleep(0.001)

        async def receiver():
            for _ in range(5):
                msgs = await bus.receive("b")
                received.extend(msgs)
                await asyncio.sleep(0.01)

        await asyncio.gather(sender(), receiver())

        # After sender finishes, drain remaining
        remaining = await bus.receive("b")
        received.extend(remaining)

        assert len(received) == 20

    @pytest.mark.asyncio
    async def test_concurrent_broadcast(self):
        bus, _ = _make_bus_with_agents(5)

        async def broadcast_one(i: int):
            await bus.broadcast(sender="agent-0", content={"i": i})

        await asyncio.gather(*[broadcast_one(i) for i in range(10)])

        for aid in ("agent-1", "agent-2", "agent-3", "agent-4"):
            msgs = await bus.receive(aid)
            assert len(msgs) == 10


class TestMessageBusRegistration:
    """Agent 注册管理"""

    def test_register_agent(self):
        bus = MessageBus()
        bus.register_agent("a")

        assert "a" in bus.registered_agents

    def test_unregister_agent(self):
        bus = MessageBus()
        bus.register_agent("a")
        bus.unregister_agent("a")

        assert "a" not in bus.registered_agents

    def test_unregister_nonexistent(self):
        bus = MessageBus()
        bus.unregister_agent("ghost")
        # Should not raise

    def test_duplicate_register(self):
        bus = MessageBus()
        bus.register_agent("a")
        bus.register_agent("a")

        assert bus.registered_agents.count("a") == 1

    def test_queue_size(self):
        bus = MessageBus()
        bus.register_agent("a")

        assert bus.queue_size("a") == 0

    @pytest.mark.asyncio
    async def test_queue_size_after_send(self):
        bus = MessageBus()
        bus.register_agent("a")
        bus.register_agent("b")

        await bus.send(AgentMessage(sender="a", receiver="b", content={}))
        await bus.send(AgentMessage(sender="a", receiver="b", content={}))

        assert bus.queue_size("b") == 2
        assert bus.queue_size("a") == 0

    def test_queue_size_unregistered(self):
        bus = MessageBus()
        assert bus.queue_size("ghost") == 0


# ═══════════════════════════════════════════════════════════
# AgentRuntime 集成测试
# ═══════════════════════════════════════════════════════════


class TestRuntimeMessageBusIntegration:
    """AgentRuntime + MessageBus 集成"""

    def test_set_message_bus(self):
        runtime = AgentRuntime()
        bus = MessageBus()
        agent = MockAgent("a1")
        runtime.register(agent)

        runtime.set_message_bus(bus)

        assert runtime.message_bus is bus

    def test_set_message_bus_registers_existing_agents(self):
        runtime = AgentRuntime()
        bus = MessageBus()
        agent1 = MockAgent("a1")
        agent2 = MockAgent("a2")
        runtime.register(agent1)
        runtime.register(agent2)

        runtime.set_message_bus(bus)

        assert "a1" in bus.registered_agents
        assert "a2" in bus.registered_agents

    def test_set_message_bus_injects_into_agents(self):
        runtime = AgentRuntime()
        bus = MessageBus()
        agent = MockAgent("a1")
        runtime.register(agent)

        runtime.set_message_bus(bus)

        assert agent._message_bus is bus

    def test_register_after_set_bus(self):
        """注册新 Agent 时自动注入 MessageBus"""
        runtime = AgentRuntime()
        bus = MessageBus()
        runtime.set_message_bus(bus)

        agent = MockAgent("late-agent")
        runtime.register(agent)

        assert "late-agent" in bus.registered_agents
        assert agent._message_bus is bus

    @pytest.mark.asyncio
    async def test_agent_send_via_runtime(self):
        runtime, bus, agents = _make_runtime_with_bus(2)

        await agents[0].send_message("agent-1", {"data": "hello"})

        msgs = await bus.receive("agent-1")
        assert len(msgs) == 1
        assert msgs[0].content == {"data": "hello"}
        assert msgs[0].sender == "agent-0"

    @pytest.mark.asyncio
    async def test_agent_receive_via_runtime(self):
        runtime, bus, agents = _make_runtime_with_bus(2)

        await bus.send(AgentMessage(
            sender="agent-1", receiver="agent-0", content={"reply": "hi"},
        ))

        msgs = await agents[0].receive_messages()
        assert len(msgs) == 1
        assert msgs[0].content == {"reply": "hi"}

    @pytest.mark.asyncio
    async def test_agent_send_receive_roundtrip(self):
        runtime, bus, agents = _make_runtime_with_bus(2)

        # agent-0 -> agent-1
        await agents[0].send_message("agent-1", {"request": "data"})
        # agent-1 receives
        received = await agents[1].receive_messages()
        assert len(received) == 1
        assert received[0].content == {"request": "data"}

        # agent-1 -> agent-0 (reply)
        await agents[1].send_message("agent-0", {"response": "here"})
        reply = await agents[0].receive_messages()
        assert len(reply) == 1
        assert reply[0].content == {"response": "here"}

    @pytest.mark.asyncio
    async def test_runtime_old_send_message_still_works(self):
        """旧的 runtime.send_message 接口仍可用"""
        runtime, bus, agents = _make_runtime_with_bus(2)

        old_msg = AgentMessage(
            sender="agent-0", receiver="agent-1", content={"old": True},
        )
        runtime.send_message(old_msg)

        msgs = runtime.receive_messages("agent-1")
        assert len(msgs) == 1
        assert msgs[0].content == {"old": True}

    @pytest.mark.asyncio
    async def test_broadcast_via_bus(self):
        runtime, bus, agents = _make_runtime_with_bus(3)

        await agents[0].send_message("agent-1", {"targeted": True})

        await bus.broadcast(sender="agent-0", content={"broadcast": True})

        msgs_1 = await bus.receive("agent-1")
        msgs_2 = await bus.receive("agent-2")

        # agent-1 has 1 targeted + 1 broadcast
        assert len(msgs_1) == 2
        # agent-2 has 1 broadcast
        assert len(msgs_2) == 1
        assert msgs_2[0].content == {"broadcast": True}


class TestBaseAgentMessageBus:
    """BaseAgent 消息方法测试"""

    @pytest.mark.asyncio
    async def test_send_message_without_bus_raises(self):
        agent = MockAgent("a1")

        with pytest.raises(RuntimeError, match="MessageBus not set"):
            await agent.send_message("receiver", {"data": 1})

    @pytest.mark.asyncio
    async def test_receive_messages_without_bus_raises(self):
        agent = MockAgent("a1")

        with pytest.raises(RuntimeError, match="MessageBus not set"):
            await agent.receive_messages()

    @pytest.mark.asyncio
    async def test_send_message_with_bus(self):
        bus = MessageBus()
        agent = MockAgent("a1")
        bus.register_agent("a1")
        bus.register_agent("a2")
        agent.set_message_bus(bus)

        await agent.send_message("a2", {"key": "value"})

        msgs = await bus.receive("a2")
        assert len(msgs) == 1
        assert msgs[0].sender == "a1"
        assert msgs[0].content == {"key": "value"}
        assert msgs[0].message_type == "data"

    @pytest.mark.asyncio
    async def test_receive_messages_with_bus(self):
        bus = MessageBus()
        agent = MockAgent("a1")
        bus.register_agent("a1")
        agent.set_message_bus(bus)

        await bus.send(AgentMessage(sender="x", receiver="a1", content={"for": "a1"}))

        msgs = await agent.receive_messages()
        assert len(msgs) == 1
        assert msgs[0].content == {"for": "a1"}