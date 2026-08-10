"""
ResearchAgent — 信息采集 Agent
负责搜索和采集热点信息。
当前为 Mock 实现，Phase 3 后续接入真实采集。
"""

from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentType, AgentStatus


class ResearchAgent(BaseAgent):
    """信息采集 Agent"""

    def __init__(self):
        config = AgentConfig(
            id="research",
            name="research",
            type=AgentType.RESEARCH,
            capabilities=["web_search", "rss_parse", "news_crawl"],
            extra={"description": "搜索和采集热点信息"},
        )
        super().__init__(config)
        self._status = AgentStatus.ONLINE

    async def chat(self, message: str, context: dict | None = None) -> str:
        return f"[ResearchAgent] 收到查询: {message}"

    async def execute_task(self, task_input: dict) -> AgentResponse:
        """
        执行采集任务
        输入: {"task": str, "context": dict}
        输出: {"agent": "research", "topics": [...], "summary": str}
        """
        task = task_input.get("task", "")

        # Mock 采集结果
        topics = [
            {"title": "AI行业最新动态", "url": "https://example.com/ai-news", "relevance": 0.95},
            {"title": "大模型技术突破", "url": "https://example.com/llm", "relevance": 0.88},
            {"title": "AI应用落地案例", "url": "https://example.com/cases", "relevance": 0.76},
        ]

        return AgentResponse(
            success=True,
            data={
                "agent": "research",
                "topics": topics,
                "summary": f"围绕「{task}」采集到 {len(topics)} 条相关信息",
            },
            agent_id=self.id,
        )

    def get_capabilities(self) -> list[str]:
        return ["web_search", "rss_parse", "news_crawl"]