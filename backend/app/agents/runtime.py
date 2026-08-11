"""
AgentRuntime — 多 Agent 运行时调度。
管理 Agent 生命周期、状态、Agent 间消息传递。
Phase 3.9.1: 集成 MessageBus，支持 Agent 间异步消息通信。
Phase 3.18: 集成 TraceCollector，记录 agent 执行开始/结束/异常事件。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TYPE_CHECKING

from app.agents.base import BaseAgent, AgentResult
from app.agents.message import AgentMessage
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.agents.message_bus import MessageBus

logger = get_logger(__name__)


class AgentState(str, Enum):
    """Agent 运行状态"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentTaskRecord:
    """单个 Agent 的运行记录"""
    agent_id: str
    state: AgentState = AgentState.IDLE
    task: str = ""
    result: Any = None
    error: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AgentRuntime:
    """
    多 Agent 运行时。
    职责：
    - Agent 注册与获取
    - Agent 生命周期管理 (initialize / shutdown)
    - Agent 状态追踪
    - Agent 间消息路由（内置队列 + 可选 MessageBus）
    - Phase 3.18: 可选 TraceCollector 追踪
    """

    def __init__(self, trace_collector: "TraceCollector | None" = None):
        self._agents: dict[str, BaseAgent] = {}
        self._states: dict[str, AgentTaskRecord] = {}
        self._message_queue: dict[str, list[AgentMessage]] = {}
        self._message_bus: "MessageBus | None" = None
        self._trace = trace_collector

    # === TraceCollector 集成 ===

    def set_trace_collector(self, collector: "TraceCollector"):
        """注入 TraceCollector 实例"""
        self._trace = collector

    # === MessageBus 集成 ===

    def set_message_bus(self, bus: "MessageBus"):
        """
        注入 MessageBus 实例。
        设置后，所有 Agent 的消息操作将通过 MessageBus 进行。
        同时自动将 MessageBus 注入到所有已注册 Agent。
        """
        self._message_bus = bus
        for agent in self._agents.values():
            agent.set_message_bus(bus)
            bus.register_agent(agent.id)
        logger.info("MessageBus set on runtime", agents=len(self._agents))

    @property
    def message_bus(self) -> "MessageBus | None":
        return self._message_bus

    # === Agent 注册 ===

    def register(self, agent: BaseAgent):
        """注册 Agent"""
        self._agents[agent.id] = agent
        self._states[agent.id] = AgentTaskRecord(agent_id=agent.id)
        self._message_queue[agent.id] = []
        # 如果已有 MessageBus，自动注册新 Agent
        if self._message_bus:
            self._message_bus.register_agent(agent.id)
            agent.set_message_bus(self._message_bus)
        logger.info("Agent registered in runtime", agent_id=agent.id)

    def get(self, agent_id: str) -> BaseAgent | None:
        """获取 Agent"""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[dict]:
        """列出所有 Agent 及其状态"""
        result = []
        for aid, agent in self._agents.items():
            record = self._states.get(aid)
            info = agent.to_dict()
            info["state"] = record.state.value if record else "unknown"
            result.append(info)
        return result

    def get_agent_status(self, agent_id: str) -> dict:
        """
        获取指定 Agent 的运行状态详情。
        Returns:
            {"agent_id", "state", "task", "started_at", "completed_at", "error"}
        """
        record = self._states.get(agent_id)
        if not record:
            return {"agent_id": agent_id, "state": "unknown"}
        return {
            "agent_id": record.agent_id,
            "state": record.state.value,
            "task": record.task,
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
            "error": record.error,
        }

    def list_running_agents(self) -> list[dict]:
        """列出所有状态为 RUNNING 的 Agent"""
        return [
            self.get_agent_status(aid)
            for aid, rec in self._states.items()
            if rec.state == AgentState.RUNNING
        ]

    # === 生命周期管理 ===

    async def initialize_agent(self, agent_id: str):
        """初始化指定 Agent"""
        agent = self._agents.get(agent_id)
        if agent:
            await agent.initialize()
            logger.info("Agent initialized", agent_id=agent_id)

    async def initialize_all(self):
        """初始化所有 Agent"""
        for agent_id in self._agents:
            await self.initialize_agent(agent_id)

    async def shutdown_agent(self, agent_id: str):
        """关闭指定 Agent"""
        agent = self._agents.get(agent_id)
        if agent:
            await agent.shutdown()
            logger.info("Agent shutdown", agent_id=agent_id)

    async def shutdown_all(self):
        """关闭所有 Agent"""
        for agent_id in self._agents:
            await self.shutdown_agent(agent_id)

    # === 状态管理 ===

    def get_state(self, agent_id: str) -> AgentState | None:
        record = self._states.get(agent_id)
        return record.state if record else None

    def set_state(self, agent_id: str, state: AgentState):
        record = self._states.get(agent_id)
        if record:
            record.state = state
            if state == AgentState.RUNNING and record.started_at is None:
                record.started_at = datetime.now(timezone.utc)
            if state in (AgentState.COMPLETED, AgentState.FAILED):
                record.completed_at = datetime.now(timezone.utc)

    def get_record(self, agent_id: str) -> AgentTaskRecord | None:
        return self._states.get(agent_id)

    # === 消息路由（内置队列，兼容旧接口） ===

    def send_message(self, msg: AgentMessage):
        """发送 Agent 间消息（内置队列）"""
        if msg.receiver in self._message_queue:
            self._message_queue[msg.receiver].append(msg)
            logger.debug("Message sent", sender=msg.sender, receiver=msg.receiver, type=msg.message_type)

    def receive_messages(self, agent_id: str) -> list[AgentMessage]:
        """接收并清空指定 Agent 的消息队列（内置队列）"""
        messages = self._message_queue.get(agent_id, [])
        self._message_queue[agent_id] = []
        return messages

    def peek_messages(self, agent_id: str) -> list[AgentMessage]:
        """查看消息（不清空）"""
        return list(self._message_queue.get(agent_id, []))

    # === 执行便捷方法 ===

    async def run_agent(self, agent_id: str, task: str, context: dict | None = None) -> AgentResult:
        """
        执行单个 Agent 任务，自动管理状态。
        Phase 3.18: 集成 TraceCollector 记录 start/end/error。
        """
        from app.orchestrator.planner import TaskStep, TaskType

        agent = self._agents.get(agent_id)
        if not agent:
            return AgentResult(success=False, error=f"Agent not found: {agent_id}")

        trace_id = self._trace.generate_trace_id() if self._trace else ""
        task_id = agent_id

        self.set_state(agent_id, AgentState.RUNNING)

        # Trace: start
        if self._trace:
            self._trace.start(trace_id, task_id, "agent", metadata={"agent_id": agent_id, "task": task})

        try:
            step = TaskStep(
                id=agent_id,
                type=TaskType.CUSTOM,
                description=task,
            )
            started = datetime.now(timezone.utc)
            output = await agent.execute_step(step, context)
            duration = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

            result = AgentResult(success=True, output=output)
            self.set_state(agent_id, AgentState.COMPLETED)

            record = self._states.get(agent_id)
            if record:
                record.result = output
                record.task = task

            # Trace: end
            if self._trace:
                self._trace.end(trace_id, task_id, "agent", duration_ms=duration, metadata={"agent_id": agent_id, "success": True})

            return result
        except Exception as e:  # noqa: BLE001 runtime wraps errors
            self.set_state(agent_id, AgentState.FAILED)

            # Trace: error
            if self._trace:
                self._trace.error(trace_id, task_id, "agent", error=str(e), metadata={"agent_id": agent_id})

            return AgentResult(success=False, error=str(e))

    async def run_parallel(self, tasks: list[tuple[str, str]]) -> dict[str, AgentResult]:
        """
        并行执行多个 Agent 任务
        Args:
            tasks: [(agent_id, task_description), ...]
        Returns:
            {agent_id: AgentResult}
        """
        async def _run(aid: str, task: str):
            return aid, await self.run_agent(aid, task)

        results = await asyncio.gather(*[_run(aid, t) for aid, t in tasks])
        return dict(results)