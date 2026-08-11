"""
RuntimeRepository — 运行时持久化仓库。

统一管理 Agent 状态、执行历史、Trace 事件、经验记录的持久化。
底层使用 StorageBackend，可切换 MemoryStorage / FileStorage。

不修改已有模块的内部接口，通过适配层实现持久化。
"""

from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from app.storage.base import StorageBackend
from app.utils.logger import get_logger

if TYPE_CHECKING:
    from app.execution.history import ExecutionHistory, HistoryEntry
    from app.observability.collector import TraceCollector
    from app.memory.experience import ExperienceMemory

logger = get_logger(__name__)


class RuntimeRepository:
    """
    运行时持久化仓库。
    
    职责：
    - Agent 状态存取（save_agent_state / get_agent_state）
    - 执行历史存取（save_execution / get_execution）
    - Trace 事件存取（save_trace / get_trace）
    - 经验记录存取（save_experience / query_experience）
    - 批量快照与恢复
    
    键命名约定：
    - agent:{agent_id}        -> AgentTaskRecord
    - exec:{task_id}:{iter}   -> HistoryEntry
    - trace:{trace_id}:{idx}  -> TraceEvent
    - exp:{task_pattern}:{ts} -> ExperienceRecord
    """

    def __init__(self, storage: StorageBackend):
        self._storage = storage

    @property
    def storage(self) -> StorageBackend:
        return self._storage

    # ── Agent State ──────────────────────────────────────────

    async def save_agent_state(self, agent_id: str, state: dict) -> None:
        """
        保存 Agent 运行状态。
        Args:
            agent_id: Agent ID
            state: 状态字典（来自 get_agent_status）
        """
        key = f"agent:{agent_id}"
        await self._storage.save(key, state)
        logger.debug("Agent state saved", agent_id=agent_id)

    async def get_agent_state(self, agent_id: str) -> dict | None:
        """
        获取 Agent 运行状态。
        Args:
            agent_id: Agent ID
        Returns:
            状态字典，不存在返回 None
        """
        key = f"agent:{agent_id}"
        return await self._storage.get(key)

    async def list_agent_states(self) -> list[dict]:
        """列出所有已保存的 Agent 状态"""
        keys = await self._storage.list_keys("agent:")
        states = []
        for key in keys:
            state = await self._storage.get(key)
            if state:
                states.append(state)
        return states

    async def delete_agent_state(self, agent_id: str) -> bool:
        """删除 Agent 状态"""
        return await self._storage.delete(f"agent:{agent_id}")

    # ── Execution History ────────────────────────────────────

    async def save_execution(self, task_id: str, iteration: int, entry: dict) -> None:
        """
        保存一次执行记录。
        Args:
            task_id: 任务 ID
            iteration: 迭代次数
            entry: HistoryEntry.to_dict()
        """
        key = f"exec:{task_id}:{iteration}"
        await self._storage.save(key, entry)
        logger.debug("Execution saved", task_id=task_id, iteration=iteration)

    async def get_execution(self, task_id: str, iteration: int) -> dict | None:
        """获取指定迭代的执行记录"""
        key = f"exec:{task_id}:{iteration}"
        return await self._storage.get(key)

    async def get_execution_history(self, task_id: str) -> list[dict]:
        """获取任务的完整执行历史"""
        keys = await self._storage.list_keys(f"exec:{task_id}:")
        entries = []
        for key in sorted(keys):
            entry = await self._storage.get(key)
            if entry:
                entries.append(entry)
        return entries

    async def list_executions(self) -> list[str]:
        """列出所有任务 ID"""
        keys = await self._storage.list_keys("exec:")
        task_ids = set()
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 2:
                task_ids.add(parts[1])
        return sorted(task_ids)

    # ── Trace Events ─────────────────────────────────────────

    async def save_trace(self, trace_id: str, index: int, event: dict) -> None:
        """
        保存一个 Trace 事件。
        Args:
            trace_id: Trace ID
            index: 事件序号
            event: TraceEvent.to_dict()
        """
        key = f"trace:{trace_id}:{index}"
        await self._storage.save(key, event)

    async def get_trace(self, trace_id: str) -> list[dict]:
        """获取完整的 Trace 链"""
        keys = await self._storage.list_keys(f"trace:{trace_id}:")
        events = []
        for key in sorted(keys):
            event = await self._storage.get(key)
            if event:
                events.append(event)
        return events

    async def save_trace_events(self, trace_id: str, events: list[dict]) -> int:
        """批量保存 Trace 事件"""
        count = 0
        for idx, event in enumerate(events):
            await self.save_trace(trace_id, idx, event)
            count += 1
        return count

    # ── Experience Records ───────────────────────────────────

    async def save_experience(self, task_pattern: str, record: dict) -> str:
        """
        保存一条经验记录。
        Args:
            task_pattern: 任务模式
            record: 经验记录字典
        Returns:
            存储键
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        key = f"exp:{task_pattern}:{ts}"
        await self._storage.save(key, record)
        logger.debug("Experience saved", pattern=task_pattern)
        return key

    async def get_experience(self, key: str) -> dict | None:
        """获取指定经验记录"""
        return await self._storage.get(key)

    async def query_experience(self, task_pattern: str, limit: int = 10) -> list[dict]:
        """
        按任务模式查询经验记录。
        支持前缀匹配。
        """
        keys = await self._storage.list_keys(f"exp:{task_pattern}")
        records = []
        for key in keys[:limit]:
            record = await self._storage.get(key)
            if record:
                records.append(record)
        return records

    async def list_experiences(self) -> list[str]:
        """列出所有经验键"""
        return await self._storage.list_keys("exp:")

    # ── Snapshot & Restore ───────────────────────────────────

    async def snapshot_from_runtime(self, runtime: "AgentRuntime") -> int:
        """
        从 AgentRuntime 快照所有 Agent 状态。
        Args:
            runtime: AgentRuntime 实例
        Returns:
            保存的 Agent 数量
        """
        count = 0
        for info in runtime.list_agents():
            agent_id = info.get("id", "")
            if agent_id:
                await self.save_agent_state(agent_id, info)
                count += 1
        logger.info("Runtime snapshot saved", agents=count)
        return count

    async def snapshot_from_history(self, history: "ExecutionHistory") -> int:
        """
        从 ExecutionHistory 快照所有记录。
        Args:
            history: ExecutionHistory 实例
        Returns:
            保存的记录数
        """
        count = 0
        for entry in history._entries:
            await self.save_execution(entry.task_id, entry.iteration, entry.to_dict())
            count += 1
        logger.info("History snapshot saved", entries=count)
        return count

    async def snapshot_from_collector(self, collector: "TraceCollector") -> int:
        """
        从 TraceCollector 快照所有事件。
        Args:
            collector: TraceCollector 实例
        Returns:
            保存的事件数
        """
        events = [e.to_dict() for e in collector._events]
        if not events:
            return 0

        # 按 trace_id 分组保存
        grouped: dict[str, list[dict]] = {}
        for event in events:
            tid = event.get("trace_id", "unknown")
            grouped.setdefault(tid, []).append(event)

        count = 0
        for trace_id, trace_events in grouped.items():
            count += await self.save_trace_events(trace_id, trace_events)
        logger.info("Trace snapshot saved", events=count)
        return count

    async def snapshot_from_experience(self, exp: "ExperienceMemory") -> int:
        """
        从 ExperienceMemory 快照所有记录。
        Args:
            exp: ExperienceMemory 实例
        Returns:
            保存的记录数
        """
        count = 0
        for rec in exp._records:
            record = {
                "task_pattern": rec.task_pattern,
                "agents": rec.agents,
                "success": rec.success,
                "duration_ms": rec.duration_ms,
                "metadata": rec.metadata,
                "created_at": rec.created_at.isoformat(),
            }
            await self.save_experience(rec.task_pattern, record)
            count += 1
        logger.info("Experience snapshot saved", records=count)
        return count