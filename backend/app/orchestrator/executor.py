"""
任务执行器 (Executor)
职责：接收单个 TaskStep，调用对应 Agent 执行，返回结果。
处理执行过程中的错误、重试和超时。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.orchestrator.planner import TaskStep, TaskType
from app.orchestrator.router import AgentInfo, AgentRouter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """单步执行结果"""
    step_id: str
    status: StepStatus
    agent_id: str
    output: dict = field(default_factory=dict)
    error: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0


class TaskExecutor:
    """
    任务执行器
    负责执行单个 TaskStep：
    1. 通过 Router 选择 Agent
    2. 调用 Agent 执行任务
    3. 收集结果，处理异常
    支持重试和超时控制。
    """

    def __init__(self, router: AgentRouter, max_retries: int = 2):
        self.router = router
        self.max_retries = max_retries

    async def execute(self, step: TaskStep, context: dict | None = None) -> StepResult:
        """
        执行单个任务步骤
        Args:
            step: 任务步骤定义
            context: 上游步骤的输出，供当前步骤使用
        Returns:
            StepResult
        """
        started_at = datetime.now(timezone.utc)
        agent = self.router.route(step.type.value, step.agent_hint)

        logger.info(
            "Executing step",
            step_id=step.id,
            task_type=step.type.value,
            agent=agent.id,
        )

        # 构建 Agent 输入
        agent_input = self._build_agent_input(step, context or {})

        # 执行 (带重试)
        last_error = ""
        for attempt in range(self.max_retries + 1):
            try:
                result = await self._call_agent(agent, step.type, agent_input)
                completed_at = datetime.now(timezone.utc)
                duration = int((completed_at - started_at).total_seconds() * 1000)

                logger.info(
                    "Step completed",
                    step_id=step.id,
                    agent=agent.id,
                    duration_ms=duration,
                )

                return StepResult(
                    step_id=step.id,
                    status=StepStatus.SUCCESS,
                    agent_id=agent.id,
                    output=result,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=duration,
                )
            except Exception as e:  # noqa: BLE001 — retry logic
                last_error = str(e)
                logger.warning(
                    "Step failed, retrying",
                    step_id=step.id,
                    attempt=attempt + 1,
                    error=last_error,
                )

        # 所有重试都失败
        completed_at = datetime.now(timezone.utc)
        duration = int((completed_at - started_at).total_seconds() * 1000)
        return StepResult(
            step_id=step.id,
            status=StepStatus.FAILED,
            agent_id=agent.id,
            error=last_error,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration,
        )

    def _build_agent_input(self, step: TaskStep, context: dict) -> dict:
        """构建 Agent 输入参数"""
        return {
            "task_id": step.id,
            "task_type": step.type.value,
            "description": step.description,
            "params": step.params,
            "upstream_context": context,
        }

    async def _call_agent(self, agent: AgentInfo, task_type: TaskType, inputs: dict) -> dict:
        """
        调用 Agent 执行任务
        当前为 Mock 实现，返回占位结果。
        Phase 3 将接入真实的 Agent 实现。
        """
        # Mock 实现 — 模拟 Agent 返回
        mock_results = {
            TaskType.RESEARCH: {
                "items": [
                    {"title": "AI行业最新动态", "url": "https://example.com/1", "summary": "待接入真实采集"},
                    {"title": "大模型技术突破", "url": "https://example.com/2", "summary": "待接入真实采集"},
                ],
                "total": 2,
                "note": "Mock: Research Agent 尚未实现",
            },
            TaskType.ANALYSIS: {
                "recommended_topic": "AI行业最新动态",
                "score": 8.5,
                "reason": "Mock: Analysis Agent 尚未实现",
            },
            TaskType.WRITING: {
                "title": "AI行业最新动态：技术突破与未来展望",
                "body": "# Mock 文章\n\n这里是 AI 生成的文章内容。当前为占位输出，等待接入真实 Writing Agent。\n\n## 要点一\n\n待实现。\n\n## 要点二\n\n待实现。",
                "word_count": 200,
                "note": "Mock: Writing Agent 尚未实现",
            },
            TaskType.IMAGE: {
                "cover_description": "科技风格封面，蓝色调，AI元素",
                "style": "modern_tech",
                "note": "Mock: Image Agent 尚未实现",
            },
            TaskType.SEO: {
                "titles": ["AI行业重大突破：改变未来的关键技术", "深度解读：AI最新进展"],
                "tags": ["AI", "人工智能", "科技", "大模型"],
                "topics": ["#AI前沿", "#科技趋势"],
                "note": "Mock: SEO Agent 尚未实现",
            },
            TaskType.CHAT: {
                "response": f"收到您的消息：{inputs.get('description', '')}。当前为 Mock 回复，等待接入真实 Agent。",
                "note": "Mock: Default Agent 尚未实现",
            },
        }

        return mock_results.get(task_type, {
            "result": "Unknown task type",
            "note": "Mock: 未匹配的任务类型",
        })