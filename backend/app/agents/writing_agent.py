"""
WritingAgent — 内容生成 Agent
负责生成文章或短视频脚本。
当前为 Mock 实现，后续接入 LLM。
"""

from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentType, AgentStatus


class WritingAgent(BaseAgent):
    """内容生成 Agent"""

    def __init__(self):
        config = AgentConfig(
            id="writing",
            name="writing",
            type=AgentType.WRITING,
            capabilities=["article_gen", "script_gen", "copywriting"],
            extra={"description": "生成文章或短视频脚本"},
        )
        super().__init__(config)
        self._status = AgentStatus.ONLINE

    async def chat(self, message: str, context: dict | None = None) -> str:
        return f"[WritingAgent] 写作请求: {message}"

    async def execute_task(self, task_input: dict) -> AgentResponse:
        """
        执行写作任务
        输入: {"task": str, "context": dict} — context 中可包含上游 analysis 输出
        输出: {"agent": "writing", "title": str, "content": str, "tags": list}
        """
        task = task_input.get("task", "")

        return AgentResponse(
            success=True,
            data={
                "agent": "writing",
                "title": f"深度解读：{task}",
                "content": (
                    f"# 深度解读：{task}\n\n"
                    f"## 引言\n\n在当前技术快速发展的背景下，{task}成为行业关注的焦点。\n\n"
                    f"## 核心要点\n\n1. 技术创新驱动行业变革\n2. 应用场景持续拓展\n3. 未来发展趋势向好\n\n"
                    f"## 总结\n\n{task}具有广阔的发展前景，值得持续关注。"
                ),
                "tags": ["AI", "科技", "深度解读"],
                "word_count": 200,
            },
            agent_id=self.id,
        )

    def get_capabilities(self) -> list[str]:
        return ["article_gen", "script_gen", "copywriting"]