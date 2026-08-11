"""
MessageBus — Agent 间消息总线。

基于 asyncio.Queue 实现，每个 Agent 独立消息队列，支持并发安全。
"""

import asyncio
from typing import TYPE_CHECKING

from app.agents.message import AgentMessage
from app.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class MessageBus:
    """
    Agent 间消息总线。

    接口：
    - send(message): 点对点发送
    - receive(agent_id): 接收并清空指定 Agent 的消息
    - broadcast(sender, content): 广播给所有已注册 Agent

    实现：
    - asyncio.Queue 保证并发安全
    - 每个 Agent 独立队列，互不干扰
    - 支持 agent -> agent, runtime -> agent, agent -> runtime
    """

    def __init__(self):
        self._queues: dict[str, asyncio.Queue[AgentMessage]] = {}
        self._lock = asyncio.Lock()

    async def _ensure_queue(self, agent_id: str) -> asyncio.Queue[AgentMessage]:
        """确保指定 Agent 的队列存在（并发安全）"""
        if agent_id not in self._queues:
            async with self._lock:
                if agent_id not in self._queues:
                    self._queues[agent_id] = asyncio.Queue()
        return self._queues[agent_id]

    async def send(self, message: AgentMessage) -> None:
        """
        发送消息到指定 Agent。

        Args:
            message: AgentMessage 实例（receiver 决定目标队列）
        """
        queue = await self._ensure_queue(message.receiver)
        await queue.put(message)
        logger.debug(
            "Message sent via bus",
            sender=message.sender,
            receiver=message.receiver,
            type=message.message_type,
        )

    async def receive(self, agent_id: str) -> list[AgentMessage]:
        """
        接收并清空指定 Agent 的所有待处理消息。

        Args:
            agent_id: 目标 Agent ID

        Returns:
            消息列表（按发送顺序）
        """
        queue = await self._ensure_queue(agent_id)
        messages: list[AgentMessage] = []

        while not queue.empty():
            try:
                msg = queue.get_nowait()
                messages.append(msg)
            except asyncio.QueueEmpty:
                break

        return messages

    async def broadcast(self, sender: str, content: dict) -> None:
        """
        广播消息到所有已注册队列的 Agent（排除发送者自身）。

        Args:
            sender: 发送者 ID
            content: 消息内容
        """
        for agent_id, queue in self._queues.items():
            if agent_id == sender:
                continue
            msg = AgentMessage(
                sender=sender,
                receiver=agent_id,
                content=content,
                message_type="broadcast",
            )
            await queue.put(msg)

        logger.debug("Broadcast sent", sender=sender, receivers=len(self._queues) - 1)

    def register_agent(self, agent_id: str) -> None:
        """
        注册 Agent 到消息总线（创建独立队列）。
        同步方法，因为 Queue 创建是即时操作。
        """
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
            logger.debug("Agent registered on bus", agent_id=agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        """注销 Agent（移除队列）"""
        self._queues.pop(agent_id, None)

    @property
    def registered_agents(self) -> list[str]:
        """返回所有已注册 Agent ID"""
        return list(self._queues.keys())

    def queue_size(self, agent_id: str) -> int:
        """返回指定 Agent 队列中的待处理消息数"""
        queue = self._queues.get(agent_id)
        return queue.qsize() if queue else 0