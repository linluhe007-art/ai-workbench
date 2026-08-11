"""
BaseAgent 抽象基类 + Agent 类型层次
所有 AI Agent 必须继承此接口。
采用 Adapter Pattern，新增 Agent 只需实现此接口。

层次结构:
    BaseAgent (抽象基类)
    ├── ChatAgent        — 对话交互
    ├── ContentAgent     — 内容生成
    ├── ResearchAgent    — 信息采集
    └── KnowledgeAgent   — 知识库操作
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

# AgentContext defined in context.py to avoid circular imports

# LLM types (lazy import to avoid circular)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.orchestrator.llm_provider import LLMProvider, LLMResponse
    from app.agents.message_bus import MessageBus
    from app.workspace.manager import WorkspaceManager


class AgentStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class AgentType(str, Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"
    IMAGE = "image"
    SEO = "seo"
    CHAT = "chat"
    KNOWLEDGE = "knowledge"
    MULTI = "multi"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Agent 配置"""
    id: str
    name: str
    type: AgentType
    model: str = ""
    api_endpoint: str = ""
    api_key_env: str = ""
    capabilities: list[str] = field(default_factory=list)
    max_concurrent: int = 5
    timeout_seconds: int = 60
    extra: dict = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Agent 统一响应"""
    success: bool
    data: dict = field(default_factory=dict)
    error: str = ""
    agent_id: str = ""
    model: str = ""
    duration_ms: int = 0
    tokens_used: int = 0
    metadata: dict = field(default_factory=dict)



@dataclass
class AgentResult:
    """
    Agent 执行结果 (轻量版)
    用于 execute(task, context) 方法的返回值。
    比 AgentResponse 更简洁，适合内部调用。
    """
    success: bool
    output: any = None
    error: str = ""
    metadata: dict = field(default_factory=dict)

class BaseAgent(ABC):
    """
    Agent 抽象基类
    定义所有 Agent 必须实现的核心接口。
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm_provider: "LLMProvider | None" = config.extra.pop("llm_provider", None)
        self._tool_registry = None
        self._message_bus = None
        self._workspace_manager = None
        self._status = AgentStatus.OFFLINE

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def description(self) -> str:
        """Agent 描述"""
        return self.config.extra.get("description", f"{self.config.name} agent")

    @property
    def status(self) -> AgentStatus:
        return self._status

    @abstractmethod
    async def chat(self, message: str, context: dict | None = None) -> str:
        """自由对话"""
        ...

    @abstractmethod
    async def execute_task(self, task_input: dict) -> AgentResponse:
        """执行结构化任务"""
        ...

    def get_capabilities(self) -> list[str]:
        """返回能力标签列表（默认读取 config.capabilities）"""
        return self.config.capabilities
    def set_llm_provider(self, provider: "LLMProvider"):
        """运行时注入 LLM Provider"""
        self.llm_provider = provider

    async def call_llm(
        self,
        prompt: str,
        system: str = "",
        context: dict | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> "LLMResponse | None":
        """
        调用 LLM 的便捷方法
        自动构建 system prompt (含 Agent 身份 + context)。
        无 LLM Provider 时返回 None，调用方可自行 fallback。
        """
        if not self.llm_provider:
            return None

        from app.orchestrator.llm_provider import LLMMessage, LLMRole

        messages: list[LLMMessage] = []

        # 构建 system prompt
        sys_parts = [f"你是 {self.name} Agent。{self.description}"]
        if context:
            mem_summary = context.get("memory_summary", "")
            if mem_summary:
                sys_parts.append(f"以下是知识库参考内容：\n{mem_summary[:2000]}")
            tags = context.get("tags", [])
            if tags:
                sys_parts.append(f"相关标签：{', '.join(tags[:10])}")
        system_prompt = "\n\n".join(sys_parts)
        messages.append(LLMMessage(role=LLMRole.SYSTEM, content=system_prompt))
        messages.append(LLMMessage(role=LLMRole.USER, content=prompt))

        return await self.llm_provider.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )


    async def execute(self, task: str, context: dict | None = None) -> "AgentResult":
        """
        执行任务的统一入口
        Args:
            task: 任务描述文本
            context: 上下文信息
        Returns:
            AgentResult
        """
        try:
            response = await self.execute_task({"task": task, "context": context or {}})
            return AgentResult(
                success=response.success,
                output=response.data,
                error=response.error,
                metadata=response.metadata,
            )
        except Exception as e:  # noqa: BLE001 — execute wraps all errors
            return AgentResult(success=False, error=str(e))
    async def execute_step(self, step: "TaskStep", context: "AgentContext | None" = None) -> dict:
        """
        Pipeline 执行入口 (带上下文)
        默认实现：调用 execute_task() 并提取 data。
        子类可覆盖此方法以直接访问 AgentContext。
        """
        from app.agents.context import AgentContext
        ctx = context or AgentContext()
        task_input = {
            "task": step.description,
            "context": {
                "step_id": step.id,
                "task_type": step.type.value,
                "upstream_results": ctx.upstream_results,
                "memory_summary": ctx.memory_summary,
                "documents": ctx.documents,
                "tags": ctx.tags,
            },
        }
        response = await self.execute_task(task_input)
        if not response.success:
            raise RuntimeError(response.error or f"Agent {self.id} execute_task failed")
        return response.data
    async def run_with_tools(
        self,
        prompt: str,
        context: dict | None = None,
        max_tool_rounds: int = 5,
    ) -> "AgentResult":
        """
        LLM + Tool Calling 循环
        流程: LLM 生成 → 检测 tool_calls → 执行工具 → 结果回传 LLM → 继续生成
        Args:
            prompt: 用户提示
            context: 上下文 (含 memory 等)
            max_tool_rounds: 最大工具调用轮数 (防无限循环)
        Returns:
            AgentResult (最终 LLM 文本输出)
        """
        from app.orchestrator.llm_provider import LLMMessage, LLMRole
        from app.tools.executor import ToolExecutor

        # 无 LLM Provider 时 fallback 到 execute_task
        if not self.llm_provider:
            response = await self.execute_task({"task": prompt, "context": context or {}})
            return AgentResult(
                success=response.success,
                output=response.data,
                error=response.error,
            )

        # 构建初始消息
        sys_parts = [f"你是 {self.name} Agent。{self.description}"]
        if context:
            mem = context.get("memory_summary", "")
            if mem:
                sys_parts.append(f"知识库参考：\n{mem[:2000]}")
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content="\n\n".join(sys_parts)),
            LLMMessage(role=LLMRole.USER, content=prompt),
        ]

        # 获取可用工具
        tools = None
        tool_executor = None
        if self._tool_registry and len(self._tool_registry) > 0:
            from app.orchestrator.llm_provider import LLMTool
            tools = [
                LLMTool(
                    name=t.name,
                    description=t.description,
                    parameters=t._parameters_schema(),
                )
                for t in self._tool_registry._tools.values()
            ]
            tool_executor = ToolExecutor(self._tool_registry)

        # Tool calling 循环
        for _ in range(max_tool_rounds):
            resp = await self.llm_provider.chat(messages=messages, tools=tools)

            # 无 tool_calls → 返回最终文本
            if not resp.tool_calls or resp.finish_reason != "tool_calls":
                return AgentResult(
                    success=True,
                    output={"response": resp.content, "model": resp.model, "tokens_used": resp.tokens_used},
                    metadata={"provider": "llm", "tool_rounds": _},
                )

            # 有 tool_calls → 解析并执行
            from app.tools.base import ToolCall
            parsed_calls = [ToolCall.from_llm_dict(tc) for tc in resp.tool_calls]

            # 添加 assistant 消息 (含 tool_calls)
            messages.append(LLMMessage(
                role=LLMRole.ASSISTANT,
                content=resp.content or "",
            ))

            # 执行工具并回传结果
            if tool_executor:
                report = await tool_executor.execute_all(parsed_calls)
                for msg in report.to_llm_messages():
                    messages.append(LLMMessage(
                        role=LLMRole.TOOL,
                        content=msg["content"],
                        tool_call_id=msg.get("tool_call_id", ""),
                    ))

        # 超过最大轮数
        return AgentResult(
            success=True,
            output={"response": messages[-1].content if messages else "", "note": "max tool rounds reached"},
        )

    def set_tool_registry(self, registry: "ToolRegistry"):
        """注入 ToolRegistry"""
        self._tool_registry = registry
    def set_message_bus(self, bus: "MessageBus"):
        """注入 MessageBus 实例"""
        self._message_bus = bus

    async def send_message(self, receiver: str, content: dict) -> None:
        """
        通过 MessageBus 发送消息给另一个 Agent。
        Args:
            receiver: 接收方 Agent ID
            content: 消息内容（dict）
        Raises:
            RuntimeError: 如果未设置 MessageBus
        """
        if not self._message_bus:
            raise RuntimeError("MessageBus not set. Call set_message_bus() first.")
        from app.agents.message import AgentMessage
        msg = AgentMessage(
            sender=self.id,
            receiver=receiver,
            content=content,
            message_type="data",
        )
        await self._message_bus.send(msg)

    async def receive_messages(self) -> list:
        """
        通过 MessageBus 接收本 Agent 的所有待处理消息。
        Returns:
            AgentMessage 列表
        Raises:
            RuntimeError: 如果未设置 MessageBus
        """
        if not self._message_bus:
            raise RuntimeError("MessageBus not set. Call set_message_bus() first.")
        return await self._message_bus.receive(self.id)






    # === Workspace 集成 ===

    def set_workspace(self, manager: "WorkspaceManager"):
        """注入 WorkspaceManager"""
        self._workspace_manager = manager

    @property
    def workspace(self) -> "WorkspaceManager | None":
        """访问 WorkspaceManager"""
        return self._workspace_manager

    async def save_artifact(
        self,
        workspace_id: str,
        name: str,
        content: any,
        item_type: str = "text",
        metadata: dict | None = None,
    ) -> "WorkspaceItem":
        """
        保存产物到工作空间。
        Raises:
            RuntimeError: 如果未设置 WorkspaceManager
        """
        if not self._workspace_manager:
            raise RuntimeError("WorkspaceManager not set. Call set_workspace() first.")
        return self._workspace_manager.save_artifact(
            workspace_id=workspace_id,
            owner=self.id,
            name=name,
            content=content,
            item_type=item_type,
            metadata=metadata,
        )

    async def get_artifact(self, workspace_id: str, item_id: str):
        """
        从工作空间获取产物。
        Raises:
            RuntimeError: 如果未设置 WorkspaceManager
        """
        if not self._workspace_manager:
            raise RuntimeError("WorkspaceManager not set. Call set_workspace() first.")
        return self._workspace_manager.get_item(workspace_id, item_id)

    async def initialize(self):
        """初始化"""
        self._status = AgentStatus.ONLINE

    async def shutdown(self):
        """关闭"""
        self._status = AgentStatus.OFFLINE

    def to_dict(self) -> dict:
        return {
            "id": self.config.id,
            "name": self.config.name,
            "type": self.config.type.value,
            "model": self.config.model,
            "capabilities": self.get_capabilities(),
            "status": self._status.value,
        }


# === 具体 Agent 类型 (抽象层) ===

class ChatAgent(BaseAgent):
    """对话交互 Agent"""
    @abstractmethod
    async def chat_stream(self, message: str, context: dict | None = None):
        """流式对话 (yield 片段)"""
        ...


class ContentAgent(BaseAgent):
    """内容生成 Agent"""
    @abstractmethod
    async def generate(self, topic: str, style: str = "", **kwargs) -> dict:
        """
        生成内容
        Returns: {"title": str, "body": str, "tags": list}
        """
        ...


class ResearchAgent(BaseAgent):
    """信息采集 Agent"""
    @abstractmethod
    async def search(self, query: str, sources: list[str] | None = None) -> list[dict]:
        """
        搜索信息
        Returns: [{"title": str, "url": str, "summary": str}]
        """
        ...


class KnowledgeAgent(BaseAgent):
    """知识库操作 Agent"""
    @abstractmethod
    async def query(self, question: str, context: dict | None = None) -> dict:
        """
        基于知识库回答问题
        Returns: {"answer": str, "sources": list}
        """
        ...