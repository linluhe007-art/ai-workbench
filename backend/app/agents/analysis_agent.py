"""
AnalysisAgent — 内容分析 Agent
负责分析采集结果的价值和选题方向。
当前为 Mock 实现。
"""

from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentType, AgentStatus


class AnalysisAgent(BaseAgent):
    """内容分析 Agent"""

    def __init__(self):
        config = AgentConfig(
            id="analysis",
            name="analysis",
            type=AgentType.ANALYSIS,
            capabilities=["content_eval", "trend_analysis", "sentiment"],
            extra={"description": "分析内容价值和选题方向"},
        )
        super().__init__(config)
        self._status = AgentStatus.ONLINE

    async def chat(self, message: str, context: dict | None = None) -> str:
        return f"[AnalysisAgent] 分析请求: {message}"

    async def execute_task(self, task_input: dict) -> AgentResponse:
        """
        执行分析任务
        输入: {"task": str, "context": dict} — context 中可包含上游 research 输出
        输出: {"agent": "analysis", "score": float, "recommendation": str, "details": dict}
        """
        task = task_input.get("task", "")
        context = task_input.get("context", {})

        # 从上游提取信息
        research_data = context.get("research", {})
        topics_count = len(research_data.get("topics", [])) if isinstance(research_data, dict) else 0

        return AgentResponse(
            success=True,
            data={
                "agent": "analysis",
                "score": 8.2,
                "recommendation": f"围绕「{task}」具有较高内容价值，建议深入AI技术突破方向",
                "details": {
                    "trend": "上升",
                    "competition": "中等",
                    "audience_interest": "高",
                    "topics_analyzed": topics_count,
                },
            },
            agent_id=self.id,
        )

    def get_capabilities(self) -> list[str]:
        return ["content_eval", "trend_analysis", "sentiment"]