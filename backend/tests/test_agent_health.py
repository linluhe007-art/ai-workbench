"""
Phase 3.9.2 测试 — Agent Heartbeat
覆盖：
- HeartbeatRecord 创建
- AgentHeartbeat beat / is_alive / check_all
- 超时检测
- 多 Agent 监控
- Runtime 集成
"""

import asyncio
import pytest

from app.agents.heartbeat import AgentHeartbeat, HeartbeatRecord


# ═══════════════════════════════════════════════════════════
# HeartbeatRecord 测试
# ═══════════════════════════════════════════════════════════


class TestHeartbeatRecord:

    def test_default_values(self):
        rec = HeartbeatRecord(agent_id="a1")
        assert rec.agent_id == "a1"
        assert rec.status == "alive"
        assert rec.beat_count == 0
        assert rec.missed_beats == 0
        assert rec.last_seen is not None


# ═══════════════════════════════════════════════════════════
# AgentHeartbeat 基本操作测试
# ═══════════════════════════════════════════════════════════


class TestHeartbeatBasic:

    def test_register(self):
        hb = AgentHeartbeat()
        hb.register("a1")
        assert "a1" in hb.registered_agents

    def test_register_idempotent(self):
        hb = AgentHeartbeat()
        hb.register("a1")
        hb.register("a1")
        assert hb.registered_agents.count("a1") == 1

    def test_unregister(self):
        hb = AgentHeartbeat()
        hb.register("a1")
        hb.unregister("a1")
        assert "a1" not in hb.registered_agents

    def test_unregister_nonexistent(self):
        hb = AgentHeartbeat()
        hb.unregister("ghost")

    def test_beat_auto_registers(self):
        hb = AgentHeartbeat()
        hb.beat("a1")
        assert "a1" in hb.registered_agents

    def test_beat_increments_count(self):
        hb = AgentHeartbeat()
        hb.beat("a1")
        hb.beat("a1")
        hb.beat("a1")
        status = hb.get_status("a1")
        assert status["beat_count"] == 3

    def test_beat_resets_missed(self):
        hb = AgentHeartbeat()
        hb.register("a1")
        hb._records["a1"].missed_beats = 5
        hb.beat("a1")
        assert hb._records["a1"].missed_beats == 0


class TestHeartbeatIsAlive:

    def test_is_alive_after_beat(self):
        hb = AgentHeartbeat()
        hb.beat("a1")
        assert hb.is_alive("a1") is True

    def test_is_alive_unregistered(self):
        hb = AgentHeartbeat()
        assert hb.is_alive("ghost") is False

    def test_is_alive_timeout(self):
        hb = AgentHeartbeat(timeout_seconds=0.01)
        hb.beat("a1")

        import time
        time.sleep(0.02)

        assert hb.is_alive("a1") is False

    def test_is_alive_within_timeout(self):
        hb = AgentHeartbeat(timeout_seconds=10.0)
        hb.beat("a1")
        assert hb.is_alive("a1") is True

    def test_beat_resets_alive(self):
        hb = AgentHeartbeat(timeout_seconds=0.01)
        hb.beat("a1")

        import time
        time.sleep(0.02)
        assert hb.is_alive("a1") is False

        hb.beat("a1")
        assert hb.is_alive("a1") is True


class TestHeartbeatCheckAll:

    def test_check_all_alive(self):
        hb = AgentHeartbeat(timeout_seconds=10.0)
        hb.beat("a1")
        hb.beat("a2")
        hb.beat("a3")

        results = hb.check_all()
        assert len(results) == 3
        assert all(r["alive"] for r in results)

    def test_check_all_some_dead(self):
        hb = AgentHeartbeat(timeout_seconds=0.01)
        hb.beat("a1")
        hb.beat("a2")

        import time
        time.sleep(0.02)
        hb.beat("a3")  # still alive

        results = hb.check_all()
        status_map = {r["agent_id"]: r["alive"] for r in results}
        assert status_map["a1"] is False
        assert status_map["a2"] is False
        assert status_map["a3"] is True

    def test_check_all_increments_missed(self):
        hb = AgentHeartbeat(timeout_seconds=0.01)
        hb.beat("a1")

        import time
        time.sleep(0.02)

        hb.check_all()
        assert hb._records["a1"].missed_beats == 1

        hb.check_all()
        assert hb._records["a1"].missed_beats == 2

    def test_check_all_empty(self):
        hb = AgentHeartbeat()
        results = hb.check_all()
        assert results == []


class TestHeartbeatGetStatus:

    def test_get_status_alive(self):
        hb = AgentHeartbeat(timeout_seconds=10.0)
        hb.beat("a1")

        status = hb.get_status("a1")
        assert status["alive"] is True
        assert status["status"] == "alive"
        assert status["beat_count"] == 1
        assert "last_seen" in status

    def test_get_status_unknown(self):
        hb = AgentHeartbeat()
        status = hb.get_status("ghost")
        assert status["alive"] is False
        assert status["status"] == "unknown"

    def test_timeout_property(self):
        hb = AgentHeartbeat(timeout_seconds=30.0)
        assert hb.timeout_seconds == 30.0


class TestHeartbeatConcurrency:

    @pytest.mark.asyncio
    async def test_concurrent_beats(self):
        hb = AgentHeartbeat()

        async def beat_many(agent_id: str, count: int):
            for _ in range(count):
                hb.beat(agent_id)

        await asyncio.gather(
            beat_many("a1", 50),
            beat_many("a2", 50),
            beat_many("a3", 50),
        )

        assert hb.get_status("a1")["beat_count"] == 50
        assert hb.get_status("a2")["beat_count"] == 50
        assert hb.get_status("a3")["beat_count"] == 50