"""
AppRuntime — 全局运行时单例。

持有 AgentRuntime、TraceCollector、ExperienceMemory、ExecutionHistory 等实例。
API 路由通过 get_runtime() 获取共享实例。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.agents.runtime import AgentRuntime
from app.agents.mock_agent import MockAgent
from app.agents.research_agent import ResearchAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.writing_agent import WritingAgent
from app.execution.history import ExecutionHistory
from app.execution.task_loop import TaskLoopManager, LoopResult
from app.memory.experience import ExperienceMemory
from app.observability.collector import TraceCollector
from app.observability.metrics import RuntimeMetrics
from app.planning.planner import Planner
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.storage.memory import MemoryStorage
from app.storage.repository import RuntimeRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """API 层任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskRecord:
    """API 层任务记录"""
    task_id: str
    task: str
    status: TaskStatus = TaskStatus.PENDING
    loop_result: LoopResult | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        result = {
            "task_id": self.task_id,
            "task": self.task,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if self.loop_result:
            result["iterations"] = self.loop_result.iterations
            result["success"] = self.loop_result.success
            result["task_id_result"] = self.loop_result.task_id
            if self.loop_result.evaluation:
                result["evaluation"] = {
                    "score": self.loop_result.evaluation.score,
                    "quality": self.loop_result.evaluation.quality,
                    "issues": self.loop_result.evaluation.issues,
                }
            if self.loop_result.final_result:
                er = self.loop_result.final_result
                result["execution"] = {
                    "status": er.status,
                    "duration_ms": er.duration_ms,
                    "success_count": er.success_count,
                    "failed_count": er.failed_count,
                }
        return result


class AppRuntime:
    """
    全局运行时单例。
    
    持有所有 Phase 3 核心组件，提供 API 层统一访问入口。
    """

    def __init__(self):
        # Phase 3 核心组件
        self.trace_collector = TraceCollector()
        self.experience = ExperienceMemory()
        self.history = ExecutionHistory()
        self.runtime = AgentRuntime(trace_collector=self.trace_collector)
        self.repository = RuntimeRepository(MemoryStorage())

        # 注册内置 Agent
        self._register_builtin_agents()

        # Planner + Executor
        self.planner = Planner.from_registry()
        self.executor = PipelineExecutor(
            agent_map={aid: agent for aid, agent in self.runtime._agents.items()},
            trace_collector=self.trace_collector,
            experience=self.experience,
        )

        # 任务存储
        self._tasks: dict[str, TaskRecord] = {}

        logger.info("AppRuntime initialized", agents=len(self.runtime._agents))

    def _register_builtin_agents(self):
        """注册内置 Agent"""
        agents = [
            MockAgent(agent_id="default"),
            ResearchAgent(),
            AnalysisAgent(),
            WritingAgent(),
        ]
        for agent in agents:
            self.runtime.register(agent)

    def create_task(self, task: str, max_iterations: int = 3) -> TaskRecord:
        """
        创建任务记录（同步，不执行）。
        返回 task_id，后续通过 run_task 异步执行。
        """
        from app.execution.history import ExecutionHistory
        task_id = ExecutionHistory.generate_task_id()
        record = TaskRecord(
            task_id=task_id,
            task=task,
            status=TaskStatus.PENDING,
        )
        self._tasks[task_id] = record
        logger.info("Task created", task_id=task_id, task=task[:50])
        return record

    async def run_task(self, task_id: str, max_iterations: int = 3) -> TaskRecord:
        """
        异步执行任务。
        更新 TaskRecord 状态和结果。
        """
        record = self._tasks.get(task_id)
        if not record:
            raise ValueError(f"Task not found: {task_id}")

        record.status = TaskStatus.RUNNING
        record.updated_at = datetime.now(timezone.utc)

        loop = TaskLoopManager(
            planner=self.planner,
            executor=self.executor,
            history=self.history,
            trace_collector=self.trace_collector,
        )

        try:
            loop_result = await loop.run(record.task, max_iterations=max_iterations)
            record.loop_result = loop_result
            record.status = TaskStatus.COMPLETED if loop_result.success else TaskStatus.FAILED
            record.updated_at = datetime.now(timezone.utc)
            logger.info("Task completed", task_id=task_id, success=loop_result.success, iterations=loop_result.iterations)
        except Exception as e:  # noqa: BLE001
            record.status = TaskStatus.FAILED
            record.updated_at = datetime.now(timezone.utc)
            logger.error("Task failed", task_id=task_id, error=str(e))
            raise

        return record

    def get_task(self, task_id: str) -> TaskRecord | None:
        """获取任务记录"""
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        """列出所有任务"""
        return [r.to_dict() for r in self._tasks.values()]

    def get_agents(self) -> list[dict]:
        """获取所有注册 Agent"""
        return self.runtime.list_agents()

    def get_trace(self, task_id: str) -> list[dict]:
        """获取任务 Trace"""
        return self.trace_collector.get_trace(task_id)

    def get_metrics(self) -> dict:
        """获取运行时指标"""
        return RuntimeMetrics(self.trace_collector).compute()

    def get_history(self, task_id: str) -> list[dict]:
        """获取执行历史"""
        return self.history.get_history(task_id)


# 全局单例
_runtime: AppRuntime | None = None


def get_runtime() -> AppRuntime:
    """获取全局 AppRuntime 单例"""
    global _runtime
    if _runtime is None:
        _runtime = AppRuntime()
    return _runtime


def reset_runtime() -> None:
    """重置全局单例（仅用于测试）"""
    global _runtime
    _runtime = None