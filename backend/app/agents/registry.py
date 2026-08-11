"""
Agent Registry
集中注册和管理所有 Agent 实例。
提供全局单例 registry，支持 register / get / list_agents。
启动时自动注册内置 Agent。
Phase 3.10.1: 集成 CapabilityRegistry，自动追踪 Agent 能力。
"""

from app.agents.base import BaseAgent
from app.agents.capability import CapabilityRegistry
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AgentRegistry:
    """
    Agent 注册中心
    管理所有已注册 Agent 的生命周期和查找。
    Phase 3.10.1: 自动同步能力到 CapabilityRegistry。
    """

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._capability_registry = CapabilityRegistry()

    def register(self, agent: BaseAgent):
        """注册 Agent (以 agent.id 为 key)，自动同步 capabilities"""
        if agent.id in self._agents:
            logger.warning("Agent already registered, overwriting", agent_id=agent.id)
        self._agents[agent.id] = agent
        # 自动注册能力
        caps = agent.get_capabilities()
        if caps:
            self._capability_registry.register(agent.id, caps)
        logger.info("Agent registered", agent_id=agent.id, name=agent.name, capabilities=caps)

    def get(self, name: str) -> BaseAgent | None:
        """
        按 id 或 name 查找 Agent
        优先匹配 id，其次匹配 name。
        """
        if name in self._agents:
            return self._agents[name]
        for agent in self._agents.values():
            if agent.name == name:
                return agent
        return None

    def list_agents(self) -> list[dict]:
        """返回所有已注册 Agent 的摘要列表"""
        return [agent.to_dict() for agent in self._agents.values()]

    def unregister(self, name: str) -> bool:
        """注销 Agent，自动清除能力"""
        if name in self._agents:
            del self._agents[name]
            self._capability_registry.unregister(name)
            logger.info("Agent unregistered", agent_id=name)
            return True
        return False

    def clear(self):
        """清空所有注册"""
        self._agents.clear()
        self._capability_registry.clear()

    @property
    def capabilities(self) -> CapabilityRegistry:
        """访问能力注册中心"""
        return self._capability_registry

    def get_agents_by_capability(self, capability: str) -> list[str]:
        """
        按能力查询可用 Agent ID。
        便捷方法，委托给 CapabilityRegistry。
        """
        return self._capability_registry.get_agents_by_capability(capability)

    def __len__(self) -> int:
        return len(self._agents)

    def __contains__(self, name: str) -> bool:
        return name in self._agents


def _register_builtin_agents(reg: AgentRegistry):
    """注册内置 Agent"""
    from app.agents.research_agent import ResearchAgent
    from app.agents.analysis_agent import AnalysisAgent
    from app.agents.writing_agent import WritingAgent

    for agent_cls in (ResearchAgent, AnalysisAgent, WritingAgent):
        agent = agent_cls()
        reg.register(agent)


# 全局单例
registry = AgentRegistry()
_register_builtin_agents(registry)