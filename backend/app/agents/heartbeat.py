"""
AgentHeartbeat — Agent 心跳检测。

监控 Agent 是否存活，支持超时判定。
用于 Runtime 定期检查各 Agent 的健康状态。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HeartbeatRecord:
    """单个 Agent 的心跳记录"""
    agent_id: str
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "alive"
    beat_count: int = 0
    missed_beats: int = 0


class AgentHeartbeat:
    """
    Agent 心跳检测器。

    接口：
    - beat(agent_id): 记录一次心跳
    - is_alive(agent_id): 判断是否存活
    - check_all(): 检查所有 Agent，标记超时
    """

    def __init__(self, timeout_seconds: float = 60.0):
        """
        Args:
            timeout_seconds: 超时阈值（秒），超过此时间未心跳视为 dead
        """
        self._timeout = timeout_seconds
        self._records: dict[str, HeartbeatRecord] = {}

    def register(self, agent_id: str) -> None:
        """注册 Agent 到心跳监控"""
        if agent_id not in self._records:
            self._records[agent_id] = HeartbeatRecord(agent_id=agent_id)

    def unregister(self, agent_id: str) -> None:
        """注销 Agent"""
        self._records.pop(agent_id, None)

    def beat(self, agent_id: str) -> None:
        """
        记录一次心跳。
        自动注册（如果尚未注册）。
        """
        if agent_id not in self._records:
            self.register(agent_id)
        record = self._records[agent_id]
        record.last_seen = datetime.now(timezone.utc)
        record.status = "alive"
        record.beat_count += 1
        record.missed_beats = 0

    def is_alive(self, agent_id: str) -> bool:
        """
        判断 Agent 是否存活。
        超过 timeout_seconds 未心跳返回 False。
        """
        record = self._records.get(agent_id)
        if not record:
            return False

        elapsed = (datetime.now(timezone.utc) - record.last_seen).total_seconds()
        return elapsed < self._timeout

    def get_status(self, agent_id: str) -> dict:
        """
        获取 Agent 心跳详情。
        Returns:
            {"agent_id", "status", "last_seen", "beat_count", "alive"}
        """
        record = self._records.get(agent_id)
        if not record:
            return {
                "agent_id": agent_id,
                "status": "unknown",
                "last_seen": None,
                "beat_count": 0,
                "alive": False,
            }

        alive = self.is_alive(agent_id)
        return {
            "agent_id": record.agent_id,
            "status": record.status if alive else "dead",
            "last_seen": record.last_seen.isoformat(),
            "beat_count": record.beat_count,
            "alive": alive,
        }

    def check_all(self) -> list[dict]:
        """
        检查所有已注册 Agent 的心跳状态。
        超时的 Agent 标记为 dead 并递增 missed_beats。
        Returns:
            list of heartbeat status dicts
        """
        results = []
        for agent_id in self._records:
            record = self._records[agent_id]
            alive = self.is_alive(agent_id)
            if not alive:
                record.status = "dead"
                record.missed_beats += 1
                logger.warning("Agent heartbeat timeout", agent_id=agent_id)
            results.append(self.get_status(agent_id))
        return results

    @property
    def timeout_seconds(self) -> float:
        return self._timeout

    @property
    def registered_agents(self) -> list[str]:
        return list(self._records.keys())