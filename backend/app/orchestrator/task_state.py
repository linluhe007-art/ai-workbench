"""
任务状态系统
定义任务状态机和 TaskRecord，为未来 WebSocket 推送和持久化做准备。
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    WAITING = "waiting"         # 等待用户审核/输入
    COMPLETED = "completed"     # 执行完成
    FAILED = "failed"           # 执行失败
    CANCELLED = "cancelled"     # 用户取消


@dataclass
class TaskRecord:
    """
    任务记录
    包含任务的完整生命周期信息。
    为 WebSocket 推送和持久化做准备。
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.PENDING
    intent: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    steps_total: int = 0
    steps_completed: int = 0
    error: str = ""
    result: dict = field(default_factory=dict)

    def update_status(self, status: TaskStatus, error: str = ""):
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        if error:
            self.error = error

    def mark_step_done(self):
        self.steps_completed += 1
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "intent": self.intent,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "steps_total": self.steps_total,
            "steps_completed": self.steps_completed,
            "error": self.error,
        }


class TaskStateStore:
    """
    任务状态存储 (内存)
    当前为内存存储，Phase 4 可持久化到 Redis/PostgreSQL。
    """

    def __init__(self):
        self._tasks: dict[str, TaskRecord] = {}

    def create(self, intent: str, steps_total: int = 0) -> TaskRecord:
        record = TaskRecord(intent=intent, steps_total=steps_total)
        self._tasks[record.task_id] = record
        return record

    def get(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def update(self, task_id: str, status: TaskStatus, **kwargs) -> TaskRecord | None:
        record = self._tasks.get(task_id)
        if record:
            record.update_status(status, **kwargs)
        return record

    def list_all(self, status: TaskStatus | None = None) -> list[TaskRecord]:
        if status:
            return [r for r in self._tasks.values() if r.status == status]
        return list(self._tasks.values())