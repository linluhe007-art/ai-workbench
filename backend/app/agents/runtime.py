"""
AgentRuntime — 多 Agent 运行时调度。
管理 Agent 生命周期、状态、Agent 间消息传递。
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.agents.base import BaseAgent, AgentResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AgentState(str, Enum):
    """Agent 运行状态"""
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentMessage:
    """
    Agent 间消息。
    用于在 Agent 之间传递上下文和结果。
    """
    sender: str
    receiver: str
    content: Any
    msg_type: str = "data"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "msg_type": self.msg_type,
            "timestamp": self.timestamp.isoformat(),
        }


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
    - Agent 间消息路由
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._states: dict[str, AgentTaskRecord] = {}
        self._message_queue: dict[str, list[AgentMessage]] = {}

    # === Agent 注册 ===

    def register(self, agent: BaseAgent):
        """注册 Agent"""
        self._agents[agent.id] = agent
        self._states[agent.id] = AgentTaskRecord(agent_id=agent.id)
        self._message_queue[agent.id] = []
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

    # === 消息路由 ===

    def send_message(self, msg: AgentMessage):
        """发送 Agent 间消息"""
        if msg.receiver in self._message_queue:
            self._message_queue[msg.receiver].append(msg)
            logger.debug("Message sent", sender=msg.sender, receiver=msg.receiver, type=msg.msg_type)

    def receive_messages(self, agent_id: str) -> list[AgentMessage]:
        """接收并清空指定 Agent 的消息队列"""
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
        使用 execute_step() 以保持与 PipelineExecutor 一致的执行路径。
        Args:
            agent_id: Agent ID
            task: 任务描述
            context: 上下文
        Returns:
            AgentResult
        """
        from app.orchestrator.planner import TaskStep, TaskType

        agent = self._agents.get(agent_id)
        if not agent:
            return AgentResult(success=False, error=f"Agent not found: {agent_id}")

        self.set_state(agent_id, AgentState.RUNNING)
        try:
            step = TaskStep(
                id=agent_id,
                type=TaskType.CUSTOM,
                description=task,
            )
            output = await agent.execute_step(step, context)

            result = AgentResult(
                success=True,
                output=output,
            )
            self.set_state(agent_id, AgentState.COMPLETED)

            record = self._states.get(agent_id)
            if record:
                record.result = output
                record.task = task

            return result
        except Exception as e:  # noqa: BLE001 runtime wraps errors
            self.set_state(agent_id, AgentState.FAILED)
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