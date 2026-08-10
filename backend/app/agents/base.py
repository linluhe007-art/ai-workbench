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

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """返回能力标签列表"""
        ...
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