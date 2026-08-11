"""
AgentLifecycleManager — Agent 生命周期管理器。

提供比 AgentRuntime 更细粒度的生命周期状态和操作：
CREATED → INITIALIZING → READY → RUNNING → STOPPING → STOPPED
                                                  ↘ FAILED
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LifecycleState(str, Enum):
    """Agent 生命周期状态"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


# 合法状态转换
_VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.CREATED: {LifecycleState.INITIALIZING, LifecycleState.FAILED},
    LifecycleState.INITIALIZING: {LifecycleState.READY, LifecycleState.FAILED},
    LifecycleState.READY: {LifecycleState.RUNNING, LifecycleState.STOPPING, LifecycleState.FAILED},
    LifecycleState.RUNNING: {LifecycleState.READY, LifecycleState.STOPPING, LifecycleState.FAILED},
    LifecycleState.STOPPING: {LifecycleState.STOPPED, LifecycleState.FAILED},
    LifecycleState.STOPPED: {LifecycleState.INITIALIZING},  # 允许重新初始化
    LifecycleState.FAILED: {LifecycleState.INITIALIZING},   # 允许重试
}


@dataclass
class LifecycleRecord:
    """单个 Agent 的生命周期记录"""
    agent_id: str
    state: LifecycleState = LifecycleState.CREATED
    error: str = ""
    state_changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[dict] = field(default_factory=list)

    def transition(self, new_state: LifecycleState, error: str = "") -> None:
        """记录状态转换"""
        self.history.append({
            "from": self.state.value,
            "to": new_state.value,
            "at": self.state_changed_at.isoformat(),
        })
        self.state = new_state
        self.error = error
        self.state_changed_at = datetime.now(timezone.utc)


class AgentLifecycleManager:
    """
    Agent 生命周期管理器。

    职责：
    - 管理 Agent 生命周期状态转换
    - 提供 initialize / shutdown / restart 操作
    - 提供 health_check 健康检查
    - 记录状态变更历史
    """

    def __init__(self):
        self._records: dict[str, LifecycleRecord] = {}

    def register(self, agent_id: str) -> LifecycleRecord:
        """注册 Agent（状态初始化为 CREATED）"""
        record = LifecycleRecord(agent_id=agent_id)
        self._records[agent_id] = record
        logger.info("Agent registered in lifecycle", agent_id=agent_id)
        return record

    def get_state(self, agent_id: str) -> LifecycleState | None:
        """获取 Agent 当前生命周期状态"""
        record = self._records.get(agent_id)
        return record.state if record else None

    def get_record(self, agent_id: str) -> LifecycleRecord | None:
        """获取完整生命周期记录"""
        return self._records.get(agent_id)

    def _transition(self, agent_id: str, new_state: LifecycleState, error: str = "") -> bool:
        """执行状态转换（带合法性校验）"""
        record = self._records.get(agent_id)
        if not record:
            logger.warning("Agent not registered in lifecycle", agent_id=agent_id)
            return False

        allowed = _VALID_TRANSITIONS.get(record.state, set())
        if new_state not in allowed:
            logger.warning(
                "Invalid lifecycle transition",
                agent_id=agent_id,
                from_state=record.state.value,
                to_state=new_state.value,
            )
            return False

        record.transition(new_state, error)
        logger.debug(
            "Lifecycle transition",
            agent_id=agent_id,
            from_state=record.history[-1]["from"],
            to_state=new_state.value,
        )
        return True

    async def initialize(self, agent_id: str, agent: Any = None) -> bool:
        """
        初始化 Agent：CREATED/STOPPED/FAILED → INITIALIZING → READY。
        Args:
            agent_id: Agent ID
            agent: BaseAgent 实例（可选，用于调用 agent.initialize()）
        Returns:
            是否成功
        """
        if not self._transition(agent_id, LifecycleState.INITIALIZING):
            return False

        try:
            if agent and hasattr(agent, "initialize"):
                await agent.initialize()
            self._transition(agent_id, LifecycleState.READY)
            logger.info("Agent initialized via lifecycle", agent_id=agent_id)
            return True
        except Exception as e:  # noqa: BLE001 lifecycle wraps errors
            self._transition(agent_id, LifecycleState.FAILED, error=str(e))
            logger.error("Agent initialization failed", agent_id=agent_id, error=str(e))
            return False

    async def shutdown(self, agent_id: str, agent: Any = None) -> bool:
        """
        关闭 Agent：READY/RUNNING → STOPPING → STOPPED。
        Args:
            agent_id: Agent ID
            agent: BaseAgent 实例（可选）
        Returns:
            是否成功
        """
        if not self._transition(agent_id, LifecycleState.STOPPING):
            return False

        try:
            if agent and hasattr(agent, "shutdown"):
                await agent.shutdown()
            self._transition(agent_id, LifecycleState.STOPPED)
            logger.info("Agent shutdown via lifecycle", agent_id=agent_id)
            return True
        except Exception as e:  # noqa: BLE001 lifecycle wraps errors
            self._transition(agent_id, LifecycleState.FAILED, error=str(e))
            return False

    async def restart(self, agent_id: str, agent: Any = None) -> bool:
        """
        重启 Agent：先 shutdown 再 initialize。
        Args:
            agent_id: Agent ID
            agent: BaseAgent 实例
        Returns:
            是否成功
        """
        shutdown_ok = await self.shutdown(agent_id, agent)
        if not shutdown_ok:
            # 如果 shutdown 失败（状态不允许），强制设为 STOPPED
            logger.warning("Force-stopping agent for restart", agent_id=agent_id)
            record = self._records.get(agent_id)
            if record:
                record.transition(LifecycleState.STOPPED, error="forced stop for restart")

        return await self.initialize(agent_id, agent)

    def health_check(self, agent_id: str) -> dict:
        """
        Agent 健康检查。
        Returns:
            {"agent_id": str, "state": str, "healthy": bool, "error": str, "last_transition": str}
        """
        record = self._records.get(agent_id)
        if not record:
            return {
                "agent_id": agent_id,
                "state": "unknown",
                "healthy": False,
                "error": "Agent not registered",
                "last_transition": "",
            }

        healthy = record.state in (LifecycleState.READY, LifecycleState.RUNNING)
        return {
            "agent_id": agent_id,
            "state": record.state.value,
            "healthy": healthy,
            "error": record.error,
            "last_transition": record.state_changed_at.isoformat(),
            "history_count": len(record.history),
        }

    def list_agents(self) -> list[dict]:
        """列出所有已注册 Agent 的健康状态"""
        return [self.health_check(aid) for aid in self._records]

    def list_by_state(self, state: LifecycleState) -> list[str]:
        """列出指定状态的所有 Agent ID"""
        return [aid for aid, rec in self._records.items() if rec.state == state]