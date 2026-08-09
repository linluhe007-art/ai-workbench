"""
Agent 路由器 (Router)
职责：根据任务类型和 Agent 能力，选择最合适的 Agent 执行任务。
支持降级和负载均衡。
"""

from dataclasses import dataclass

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AgentInfo:
    """Agent 信息 (路由器内部使用)"""
    id: str
    name: str
    capabilities: list[str]
    status: str = "online"          # online / offline / busy
    priority: int = 0               # 优先级，越大越优先
    max_concurrent: int = 5
    current_load: int = 0


# Agent → 能力映射表
# 当前为静态配置，后续从数据库/配置文件加载
AGENT_REGISTRY: dict[str, AgentInfo] = {
    "research": AgentInfo(
        id="research-agent",
        name="Research Agent",
        capabilities=["web_search", "rss_parse", "news_crawl"],
        priority=10,
    ),
    "analysis": AgentInfo(
        id="analysis-agent",
        name="Analysis Agent",
        capabilities=["content_eval", "trend_analysis", "sentiment"],
        priority=10,
    ),
    "writing": AgentInfo(
        id="writing-agent",
        name="Writing Agent",
        capabilities=["article_gen", "script_gen", "copywriting"],
        priority=10,
    ),
    "image": AgentInfo(
        id="image-agent",
        name="Image Agent",
        capabilities=["cover_gen", "image_edit"],
        priority=5,
    ),
    "seo": AgentInfo(
        id="seo-agent",
        name="SEO Agent",
        capabilities=["title_gen", "tag_suggest"],
        priority=10,
    ),
    "default": AgentInfo(
        id="default-agent",
        name="Default Agent",
        capabilities=["chat", "general"],
        priority=0,
    ),
}


class AgentRouter:
    """
    Agent 路由器
    根据任务类型和 Agent 能力标签，选择最佳 Agent。
    支持：
    - 按能力匹配
    - 按优先级排序
    - 按负载均衡
    - Agent 降级
    """

    def __init__(self):
        self.registry = dict(AGENT_REGISTRY)

    def route(self, task_type: str, required_capability: str = "") -> AgentInfo:
        """
        选择最佳 Agent
        Args:
            task_type: 任务类型 (research/analysis/writing/image/seo/chat)
            required_capability: 所需的具体能力标签
        Returns:
            最匹配的 AgentInfo
        """
        # 1. 直接匹配 task_type
        if task_type in self.registry:
            agent = self.registry[task_type]
            if agent.status == "online":
                logger.info("Agent routed", task=task_type, agent=agent.id)
                return agent

        # 2. 按能力匹配
        if required_capability:
            candidates = [
                a for a in self.registry.values()
                if required_capability in a.capabilities and a.status == "online"
            ]
            if candidates:
                best = sorted(candidates, key=lambda a: (-a.priority, a.current_load))[0]
                logger.info("Agent routed by capability", capability=required_capability, agent=best.id)
                return best

        # 3. 降级到默认 Agent
        logger.warning("No matching agent, falling back to default", task=task_type)
        return self.registry["default"]

    def register_agent(self, key: str, agent: AgentInfo):
        """动态注册 Agent"""
        self.registry[key] = agent
        logger.info("Agent registered", key=key, agent_id=agent.id)

    def unregister_agent(self, key: str):
        """注销 Agent"""
        if key in self.registry:
            del self.registry[key]
            logger.info("Agent unregistered", key=key)

    def list_agents(self) -> list[dict]:
        """列出所有已注册 Agent"""
        return [
            {
                "id": a.id,
                "name": a.name,
                "capabilities": a.capabilities,
                "status": a.status,
                "load": f"{a.current_load}/{a.max_concurrent}",
            }
            for a in self.registry.values()
        ]

    def update_status(self, key: str, status: str):
        """更新 Agent 状态"""
        if key in self.registry:
            self.registry[key].status = status