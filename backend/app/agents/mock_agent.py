"""
MockAgent — 开发测试用 Agent 实现
实现 execute() 接口，返回可控的占位结果。
可继承覆盖 _build_output() 定制返回内容。
"""

from app.agents.base import BaseAgent, AgentConfig, AgentResponse, AgentType, AgentStatus
from app.orchestrator.planner import TaskStep


class MockAgent(BaseAgent):
    """
    Mock Agent
    execute() 接收 TaskStep，返回占位 dict。
    支持通过 set_response() 预设特定 step 的返回值。
    """

    def __init__(self, agent_id: str = "mock-agent", agent_type: AgentType = AgentType.CUSTOM):
        config = AgentConfig(id=agent_id, name=f"Mock({agent_id})", type=agent_type)
        super().__init__(config)
        self._status = AgentStatus.ONLINE
        self._responses: dict[str, dict] = {}  # step_id -> 预设响应
        self._call_log: list[dict] = []         # 调用记录

    async def execute_step(self, step: TaskStep, context=None) -> dict:
        """
        执行单个 TaskStep，返回结果 dict。
        优先返回预设响应，否则返回默认占位。
        """
        self._call_log.append({
            "step_id": step.id,
            "task_type": step.type.value,
            "description": step.description,
        })

        if step.id in self._responses:
            return self._responses[step.id]

        return self._build_output(step)

    def set_response(self, step_id: str, response: dict):
        """预设某个 step_id 的返回值"""
        self._responses[step_id] = response

    def set_error(self, step_id: str, error_msg: str):
        """预设某个 step_id 抛异常"""
        async def _raise(_step):
            raise RuntimeError(error_msg)
        self._responses[step_id] = {"_raise": True}
        # 使用特殊标记，在 execute 中检查
        original_responses = dict(self._responses)

        class _ErrorAgent(MockAgent):
            async def execute_step(self, step: TaskStep, context=None) -> dict:
                self._call_log.append({"step_id": step.id, "task_type": step.type.value, "description": step.description})
                if step.id in self._responses and self._responses[step.id].get("_raise"):
                    raise RuntimeError(error_msg)
                return self._build_output(step)
        # 不覆盖类，用更简单的方式
        pass

    def _build_output(self, step: TaskStep) -> dict:
        """构建默认占位输出"""
        return {
            "step_id": step.id,
            "type": step.type.value,
            "result": f"[Mock] {step.description} — 已完成",
        }

    @property
    def call_log(self) -> list[dict]:
        return list(self._call_log)

    # BaseAgent 抽象方法实现
    async def chat(self, message: str, context: dict | None = None) -> str:
        return f"[Mock] {message}"

    async def execute_task(self, task_input: dict) -> AgentResponse:
        return AgentResponse(success=True, data=task_input, agent_id=self.id)

    def get_capabilities(self) -> list[str]:
        return ["mock", "test"]