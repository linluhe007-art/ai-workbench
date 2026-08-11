"""
CapabilityRegistry — Agent 能力注册中心。

管理 Agent 与能力标签的映射关系，支持按能力查询可用 Agent。
与 AgentRegistry 配合使用，为 Orchestrator 的任务路由提供能力索引。
"""

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CapabilityRegistry:
    """
    Agent 能力注册中心。

    职责：
    - 注册 / 注销 Agent 能力
    - 按能力查询 Agent 列表
    - 查询 Agent 的所有能力
    - 全局能力索引
    """

    def __init__(self):
        # agent_id -> set of capabilities
        self._agent_caps: dict[str, set[str]] = {}
        # capability -> set of agent_ids（反向索引）
        self._cap_agents: dict[str, set[str]] = {}

    def register(self, agent_id: str, capabilities: list[str]) -> None:
        """
        注册 Agent 能力。
        支持重复调用（追加能力）。
        Args:
            agent_id: Agent ID
            capabilities: 能力标签列表
        """
        if agent_id not in self._agent_caps:
            self._agent_caps[agent_id] = set()

        for cap in capabilities:
            self._agent_caps[agent_id].add(cap)
            if cap not in self._cap_agents:
                self._cap_agents[cap] = set()
            self._cap_agents[cap].add(agent_id)

        logger.debug("Capabilities registered", agent_id=agent_id, capabilities=capabilities)

    def unregister(self, agent_id: str) -> None:
        """
        注销 Agent 的所有能力。
        Args:
            agent_id: Agent ID
        """
        caps = self._agent_caps.pop(agent_id, set())
        for cap in caps:
            if cap in self._cap_agents:
                self._cap_agents[cap].discard(agent_id)
                if not self._cap_agents[cap]:
                    del self._cap_agents[cap]
        logger.debug("Capabilities unregistered", agent_id=agent_id)

    def get_agents_by_capability(self, capability: str) -> list[str]:
        """
        按能力查询可用 Agent。
        Args:
            capability: 能力标签
        Returns:
            具备该能力的 Agent ID 列表
        """
        agents = self._cap_agents.get(capability, set())
        return list(agents)

    def get_capabilities(self, agent_id: str) -> list[str]:
        """
        查询 Agent 的所有能力。
        Args:
            agent_id: Agent ID
        Returns:
            能力标签列表
        """
        caps = self._agent_caps.get(agent_id, set())
        return list(caps)

    def list_capabilities(self) -> dict:
        """
        全局能力索引。
        Returns:
            {capability: [agent_id, ...]}
        """
        return {cap: list(agents) for cap, agents in self._cap_agents.items()}

    def has_capability(self, agent_id: str, capability: str) -> bool:
        """
        检查 Agent 是否具备指定能力。
        Args:
            agent_id: Agent ID
            capability: 能力标签
        Returns:
            bool
        """
        return capability in self._agent_caps.get(agent_id, set())

    def clear(self) -> None:
        """清空所有数据"""
        self._agent_caps.clear()
        self._cap_agents.clear()

    def __len__(self) -> int:
        """返回已注册 Agent 数量"""
        return len(self._agent_caps)