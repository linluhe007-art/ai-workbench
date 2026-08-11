"""
ExecutionHistory — 执行历史记录器。

记录每次执行迭代的完整上下文，支持回溯和分析。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HistoryEntry:
    """单次执行历史记录"""
    task_id: str
    iteration: int
    plan_intent: str
    step_count: int
    success: bool
    status: str
    duration_ms: int = 0
    failed_steps: list[str] = field(default_factory=list)
    error: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "iteration": self.iteration,
            "plan_intent": self.plan_intent,
            "step_count": self.step_count,
            "success": self.success,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "failed_steps": self.failed_steps,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


class ExecutionHistory:
    """
    执行历史记录器。

    职责：
    - 记录每次执行迭代
    - 按 task_id 查询历史
    - 提供迭代统计
    """

    def __init__(self):
        self._entries: list[HistoryEntry] = []

    def record(
        self,
        task_id: str,
        iteration: int,
        plan_intent: str,
        step_count: int,
        success: bool,
        status: str,
        duration_ms: int = 0,
        failed_steps: list[str] | None = None,
        error: str = "",
        metadata: dict | None = None,
    ) -> HistoryEntry:
        """记录一次执行"""
        entry = HistoryEntry(
            task_id=task_id,
            iteration=iteration,
            plan_intent=plan_intent,
            step_count=step_count,
            success=success,
            status=status,
            duration_ms=duration_ms,
            failed_steps=failed_steps or [],
            error=error,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        logger.debug("History recorded", task_id=task_id, iteration=iteration, success=success)
        return entry

    def get_history(self, task_id: str) -> list[dict]:
        """获取指定任务的执行历史"""
        entries = [e for e in self._entries if e.task_id == task_id]
        return [e.to_dict() for e in entries]

    def get_last(self, task_id: str) -> HistoryEntry | None:
        """获取最后一次执行记录"""
        entries = [e for e in self._entries if e.task_id == task_id]
        return entries[-1] if entries else None

    def get_iteration_count(self, task_id: str) -> int:
        """获取任务的迭代次数"""
        return sum(1 for e in self._entries if e.task_id == task_id)

    def get_success_rate(self, task_id: str) -> float:
        """获取任务的成功率"""
        entries = [e for e in self._entries if e.task_id == task_id]
        if not entries:
            return 0.0
        return sum(1 for e in entries if e.success) / len(entries)

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    @staticmethod
    def generate_task_id() -> str:
        """生成唯一的 task_id"""
        return f"task-{uuid.uuid4().hex[:8]}"