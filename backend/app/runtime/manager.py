"""
AppRuntime - global singleton.
Phase 4.11: Task lifecycle control, concurrency, timeout.
Phase 4.12: TaskEvent store, request ID, unified events.
Phase 4.13: AuditLogger integration.
Phase 4.19: Persistence integration, health tracking, event bridge, graceful shutdown.
"""

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.agents.runtime import AgentRuntime
from app.agents.mock_agent import MockAgent
from app.agents.research_agent import ResearchAgent
from app.agents.analysis_agent import AnalysisAgent
from app.agents.writing_agent import WritingAgent
from app.audit.audit_log import AuditLogger, get_audit_logger
from app.execution.history import ExecutionHistory
from app.execution.task_loop import TaskLoopManager, LoopResult
from app.execution.task_events import TaskEventStore, TaskEventType
from app.memory.experience import ExperienceMemory
from app.learning.experience_engine import ExperienceEngine
from app.openapi.webhooks import get_webhook_manager
from app.observability.collector import TraceCollector
from app.observability.metrics import RuntimeMetrics
from app.observability.metrics_collector import get_metrics_collector
from app.planning.planner import Planner
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.storage.memory import MemoryStorage
from app.storage.repository import RuntimeRepository
from app.artifacts.extractor import ArtifactExtractor
from app.workspace.manager import WorkspaceManager
from app.utils.logger import get_logger

logger = get_logger(__name__)

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"queued", "running"},
    "queued": {"running", "cancelled"},
    "running": {"paused", "completed", "failed", "cancelled", "timeout"},
    "paused": {"running", "cancelled"},
    "completed": {"queued"},
    "failed": {"queued"},
    "cancelled": {"queued"},
    "timeout": {"queued"},
}


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TaskRecord:
    task_id: str
    task: str
    status: TaskStatus = TaskStatus.PENDING
    loop_result: LoopResult | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    max_iterations: int = 3
    timeout_seconds: int | None = None
    attempt: int = 0
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    pause_event: asyncio.Event = field(default_factory=asyncio.Event)
    error_message: str | None = None

    def can_transition(self, new_status: str) -> bool:
        allowed = _VALID_TRANSITIONS.get(self.status.value, set())
        return new_status in allowed

    def to_dict(self) -> dict:
        result = {
            "task_id": self.task_id,
            "task": self.task,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "attempt": self.attempt,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
        }
        if self.error_message:
            result["error_message"] = self.error_message
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


class TaskQueue:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._running: dict[str, asyncio.Task] = {}
        self._pending_queue: list[str] = []
        self._lock = asyncio.Lock()

    @property
    def running_count(self) -> int:
        return len(self._running)

    @property
    def queued_count(self) -> int:
        return len(self._pending_queue)

    def queue_status(self) -> dict:
        return {
            "max_concurrent": self.max_concurrent,
            "running": self.running_count,
            "queued": self.queued_count,
            "running_tasks": list(self._running.keys()),
            "queued_tasks": list(self._pending_queue),
        }

    async def submit(self, task_id: str, coro, runtime: "AppRuntime") -> None:
        async with self._lock:
            if self.running_count < self.max_concurrent:
                self._start_task(task_id, coro, runtime)
            else:
                self._pending_queue.append(task_id)
                record = runtime.get_task(task_id)
                if record:
                    record.status = TaskStatus.QUEUED
                    record.updated_at = datetime.now(timezone.utc)
                logger.info("Task queued", task_id=task_id, position=len(self._pending_queue))

    def _start_task(self, task_id: str, coro, runtime: "AppRuntime") -> None:
        async def _wrapper():
            try:
                await coro
            finally:
                await self._on_task_done(task_id, runtime)
        task = asyncio.create_task(_wrapper())
        self._running[task_id] = task

    async def _on_task_done(self, task_id: str, runtime: "AppRuntime") -> None:
        async with self._lock:
            self._running.pop(task_id, None)
            if self._pending_queue:
                next_id = self._pending_queue.pop(0)
                next_record = runtime.get_task(next_id)
                if next_record and next_record.status == TaskStatus.QUEUED:
                    logger.info("Dequeuing task", task_id=next_id)
                    runtime._execute_task_async(next_id, next_record.max_iterations, self)

    async def cancel_task(self, task_id: str) -> bool:
        async with self._lock:
            if task_id in self._pending_queue:
                self._pending_queue.remove(task_id)
                return True
            atask = self._running.get(task_id)
            if atask:
                atask.cancel()
                return True
        return False


class AppRuntime:
    def __init__(self):
        self.trace_collector = TraceCollector()
        self.experience = ExperienceMemory()
        self.history = ExecutionHistory()
        self.runtime = AgentRuntime(trace_collector=self.trace_collector)
        self.repository = RuntimeRepository(MemoryStorage())
        self.artifact_extractor = ArtifactExtractor()
        self.workspace_manager = WorkspaceManager()
        self.task_queue = TaskQueue(max_concurrent=3)
        self.event_store = TaskEventStore()
        self.audit_logger: AuditLogger = get_audit_logger()
        self.metrics_collector = get_metrics_collector()
        self._experience_engine: ExperienceEngine | None = None

        self._register_builtin_agents()

        self.planner = Planner.from_registry()
        self.executor = PipelineExecutor(
            agent_map={aid: agent for aid, agent in self.runtime._agents.items()},
            trace_collector=self.trace_collector,
            experience=self.experience,
        )

        self.instance_id = os.environ.get("RUNTIME_INSTANCE_ID", f"instance-{uuid.uuid4().hex[:8]}")
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._tasks: dict[str, TaskRecord] = {}
        self._shutting_down = False

        self.persistence_enabled = os.environ.get("PERSISTENCE_ENABLED", "true").lower() in ("1", "true", "yes")
        self.redis_enabled = os.environ.get("REDIS_ENABLED", "true").lower() in ("1", "true", "yes")
        self.shutdown_timeout = int(os.environ.get("SHUTDOWN_TIMEOUT_SECONDS", "30"))

        self._health_tracker = None
        self._event_bridge = None
        self._event_bus = None
        self._distributed_lock_manager = None
        self._distributed_state = None
        self._redis_client = None
        self._recovery_manager = None
        self._task_service = None
        self._execution_service = None
        self._artifact_service = None
        self._audit_service = None
        self._ws_broadcast: Any = None

        logger.info("AppRuntime initialized", agents=len(self.runtime._agents))

    def set_ws_broadcast(self, broadcast_fn) -> None:
        self._ws_broadcast = broadcast_fn

    def _register_builtin_agents(self):
        agents = [
            MockAgent(agent_id="default"),
            ResearchAgent(),
            AnalysisAgent(),
            WritingAgent(),
        ]
        for agent in agents:
            self.runtime.register(agent)

    def create_task(self, task: str, max_iterations: int = 3) -> TaskRecord:
        task_id = ExecutionHistory.generate_task_id()
        record = TaskRecord(
            task_id=task_id,
            task=task,
            status=TaskStatus.PENDING,
            max_iterations=max_iterations,
        )
        self._tasks[task_id] = record
        self.event_store.publish(
            task_id, TaskEventType.TASK_CREATED.value, "pending",
            payload={"task": task[:200]},
        )
        self.audit_logger.record(
            actor="system",
            action="create_task",
            resource_type="task",
            resource_id=task_id,
            task_id=task_id,
        )
        self.metrics_collector.increment("tasks_created_total")
        logger.info("Task created", task_id=task_id, task=task[:50])



    # ----------------------------------------------------------------
    # Phase 4.19: Runtime Initialization
    # ----------------------------------------------------------------

    async def initialize(self) -> dict:
        from app.runtime.health import RuntimeHealthTracker
        self._health_tracker = RuntimeHealthTracker(instance_id=self.instance_id)
        result = {"instance_id": self.instance_id, "persistence": "disabled", "redis": "disabled", "recovery": "skipped", "status": "initialized"}
        if self.persistence_enabled:
            db_ok = await self._health_tracker.check_db()
            result["persistence"] = "healthy" if db_ok else "unavailable"
            if db_ok:
                await self._init_persistence_services()
            else:
                logger.warning("PostgreSQL unavailable, running in degraded mode")
                self.persistence_enabled = False
        if self.redis_enabled:
            redis_ok = await self._health_tracker.check_redis()
            result["redis"] = "healthy" if redis_ok else "unavailable"
            if redis_ok:
                await self._init_redis_services()
            else:
                logger.warning("Redis unavailable, running in degraded mode")
                self.redis_enabled = False
        await self._health_tracker.check_all()
        await self._run_recovery()
        result["recovery"] = "completed"
        if self.redis_enabled and self._distributed_state:
            try:
                await self._distributed_state.register_instance(self.instance_id, {"started_at": self.started_at})
            except Exception:
                pass
        if self.redis_enabled and self._event_bridge:
            await self._event_bridge.start_listener(self._event_bus)
        self._health_tracker.set_ready()
        result["status"] = "ready"
        logger.info("Runtime initialized", **result)
        return result

    async def _init_persistence_services(self) -> None:
        try:
            from app.persistence.task_service import PersistentTaskService
            from app.persistence.execution_service import PersistentExecutionService
            from app.persistence.artifact_service import PersistentArtifactService
            from app.persistence.audit_service import PersistentAuditService
            self._task_service = PersistentTaskService()
            self._execution_service = PersistentExecutionService()
            self._artifact_service = PersistentArtifactService()
            self._audit_service = PersistentAuditService()
            logger.info("Persistence services initialized")
        except Exception as e:
            logger.warning("Failed to init persistence services", error=str(e)[:100])

    async def _init_redis_services(self) -> None:
        try:
            from app.infrastructure.redis_client import RedisClient
            from app.infrastructure.event_bus import DistributedEventBus
            from app.infrastructure.distributed_lock import LockManager
            from app.infrastructure.state_manager import DistributedStateManager
            from app.execution.event_bridge import EventBridge
            self._redis_client = RedisClient()
            await self._redis_client.connect()
            self._event_bus = DistributedEventBus(self._redis_client, self.instance_id)
            self._distributed_lock_manager = LockManager(self._redis_client)
            self._distributed_state = DistributedStateManager(self._redis_client)
            self._event_bridge = EventBridge(instance_id=self.instance_id)
            self._event_bridge.set_event_bus(self._event_bus)
            logger.info("Redis services initialized")
        except Exception as e:
            logger.warning("Failed to init Redis services", error=str(e)[:100])

    async def _run_recovery(self) -> None:
        try:
            from app.persistence.recovery import RuntimeRecoveryManager
            self._recovery_manager = RuntimeRecoveryManager()
            recovery_result = await self._recovery_manager.recover()
            if recovery_result.get("recovered"):
                tasks = recovery_result.get("recovered_tasks", [])
                for task_data in tasks:
                    tid = task_data.get("task_id", "")
                    status = task_data.get("status", "")
                    if not tid:
                        continue
                    record = TaskRecord(
                        task_id=tid,
                        task=task_data.get("task", ""),
                        status=TaskStatus(status) if status in TaskStatus._value2member_map_ else TaskStatus.PENDING,
                        max_iterations=task_data.get("max_iterations", 3),
                        attempt=task_data.get("attempt", 0),
                    )
                    self._tasks[tid] = record
                    if status in ("running", "queued"):
                        record.status = TaskStatus.QUEUED
                        self.event_store.publish(tid, TaskEventType.TASK_QUEUED.value, "queued")
                        await self.task_queue.submit(tid, self._run_task_internal(tid, record.max_iterations), self)
                logger.info("Runtime recovery completed", tasks=len(tasks))
        except Exception as e:
            logger.warning("Runtime recovery skipped", error=str(e)[:100])

    async def _persist_task_creation(self, task_id: str, task: str, max_iterations: int) -> None:

        if not self.persistence_enabled or not self._task_service:
            return
        try:
            await self._task_service.create_task(task_id=task_id, task_text=task, max_iterations=max_iterations)
        except Exception:
            logger.warning("Failed to persist task creation", task_id=task_id)

    async def _persist_task_status(self, task_id: str, status: str, error: str = "") -> None:
        if not self.persistence_enabled or not self._task_service:
            return
        try:
            await self._task_service.update_status(task_id, status, error_message=error)
        except Exception:
            logger.warning("Failed to persist task status", task_id=task_id, status=status)

    async def _persist_audit(self, actor, action, resource_type, resource_id, task_id="", before=None, after=None, metadata=None) -> None:
        if not self.persistence_enabled or not self._audit_service:
            return
        try:
            await self._audit_service.record(actor=actor, action=action, resource_type=resource_type, resource_id=resource_id, task_id=task_id, before=before, after=after, metadata=metadata)
        except Exception:
            pass

    def _publish_task_event(self, task_id: str, event_type: str, data = None) -> None:
        if not self.redis_enabled or not self._event_bus:
            return
        import asyncio
        asyncio.create_task(self._event_bus.publish_task_event(task_id, event_type, data))

    async def submit_task(self, task_id: str, max_iterations: int = 3) -> TaskRecord:

        record = self._tasks.get(task_id)
        if not record:
            raise ValueError(f"Task not found: {task_id}")
        record.max_iterations = max_iterations
        await self.task_queue.submit(
            task_id,
            self._run_task_internal(task_id, max_iterations),
            self,
        )
        return record

    def _execute_task_async(self, task_id: str, max_iterations: int, queue: TaskQueue) -> None:
        async def _wrapper():
            await self._run_task_internal(task_id, max_iterations)
        atask = asyncio.create_task(_wrapper())
        queue._running[task_id] = atask

    async def run_task(self, task_id: str, max_iterations: int = 3) -> TaskRecord:
        return await self._run_task_internal(task_id, max_iterations)

    async def _run_task_internal(self, task_id: str, max_iterations: int) -> TaskRecord:
        record = self._tasks.get(task_id)
        if not record:
            raise ValueError(f"Task not found: {task_id}")

        record.status = TaskStatus.RUNNING
        record.attempt += 1
        record.updated_at = datetime.now(timezone.utc)
        record.cancel_event.clear()
        record.pause_event.set()

        self.event_store.publish(
            task_id, TaskEventType.TASK_STARTED.value, "running",
            attempt=record.attempt,
        )
        await self._ws_emit("task_started", task_id, {"attempt": record.attempt})
        await self._persist_task_status(task_id, "running")
        self.audit_logger.record(
            actor="system",
            action="task_started",
            resource_type="task",
            resource_id=task_id,
            task_id=task_id,
            metadata={"attempt": record.attempt},
        )

        loop = TaskLoopManager(
            planner=self.planner,
            executor=self.executor,
            history=self.history,
            trace_collector=self.trace_collector,
            artifact_extractor=self.artifact_extractor,
            workspace_manager=self.workspace_manager,
            cancel_event=record.cancel_event,
            pause_event=record.pause_event,
        )

        try:
            if record.timeout_seconds:
                loop_result = await asyncio.wait_for(
                    loop.run(record.task, max_iterations=max_iterations),
                    timeout=record.timeout_seconds,
                )
            else:
                loop_result = await loop.run(record.task, max_iterations=max_iterations)

            if record.cancel_event.is_set():
                record.status = TaskStatus.CANCELLED
                record.updated_at = datetime.now(timezone.utc)
                self.event_store.publish(task_id, TaskEventType.TASK_CANCELLED.value, "cancelled", attempt=record.attempt)
                await self._ws_emit("task_cancelled", task_id, {})
                self.audit_logger.record(
                    actor="system",
                    action="task_cancelled",
                    resource_type="task",
                    resource_id=task_id,
                    task_id=task_id,
                )
            else:
                record.loop_result = loop_result
                record.status = TaskStatus.COMPLETED if loop_result.success else TaskStatus.FAILED
                if loop_result.success:
                    self.metrics_collector.increment("tasks_completed_total")
                else:
                    self.metrics_collector.increment("tasks_failed_total")
                record.updated_at = datetime.now(timezone.utc)
                etype = TaskEventType.TASK_COMPLETED.value if loop_result.success else TaskEventType.TASK_FAILED.value
                self.event_store.publish(task_id, etype, record.status.value, attempt=record.attempt)
                event = "task_completed" if loop_result.success else "task_failed"
                await self._ws_emit(event, task_id, {"iterations": loop_result.iterations})
                await self._dispatch_webhook("task.completed" if loop_result.success else "task.failed", task_id, {"iterations": loop_result.iterations})
                self.audit_logger.record(
                    actor="system",
                    action="task_completed" if loop_result.success else "task_failed",
                    resource_type="task",
                    resource_id=task_id,
                    task_id=task_id,
                    metadata={"status": record.status.value, "iterations": loop_result.iterations},
                )

                        # Auto-record experience
            if self._experience_engine is None:
                self._experience_engine = ExperienceEngine(self.experience)
            self._experience_engine.record_experience(
                task_pattern=record.task[:200],
                agents=list(self.runtime._agents.keys()),
                success=record.status == TaskStatus.COMPLETED,
                duration_ms=0,
                metadata={"task_id": task_id, "status": record.status.value},
            )

            logger.info("Task finished", task_id=task_id, status=record.status.value, attempt=record.attempt)

        except asyncio.TimeoutError:
            self.metrics_collector.increment("tasks_timeout_total")
            record.updated_at = datetime.now(timezone.utc)
            record.error_message = f"Timeout after {record.timeout_seconds}s"
            self.event_store.publish(task_id, TaskEventType.TASK_TIMEOUT.value, "timeout", attempt=record.attempt)
            await self._ws_emit("task_timeout", task_id, {"timeout_seconds": record.timeout_seconds})
            await self._dispatch_webhook("task.failed", task_id, {"reason": "timeout", "timeout_seconds": record.timeout_seconds})
            self.audit_logger.record(
                actor="system",
                action="task_timeout",
                resource_type="task",
                resource_id=task_id,
                task_id=task_id,
                metadata={"timeout_seconds": record.timeout_seconds},
            )
            logger.warning("Task timeout", task_id=task_id, timeout=record.timeout_seconds)

        except asyncio.CancelledError:
            self.metrics_collector.increment("tasks_cancelled_total")
            record.updated_at = datetime.now(timezone.utc)
            self.event_store.publish(task_id, TaskEventType.TASK_CANCELLED.value, "cancelled", attempt=record.attempt)
            await self._ws_emit("task_cancelled", task_id, {})
            self.audit_logger.record(
                actor="system",
                action="task_cancelled",
                resource_type="task",
                resource_id=task_id,
                task_id=task_id,
            )
            logger.info("Task cancelled", task_id=task_id)

        except Exception as e:  # noqa: BLE001
            self.metrics_collector.increment("tasks_failed_total")
            record.updated_at = datetime.now(timezone.utc)
            record.error_message = str(e)
            self.event_store.publish(task_id, TaskEventType.TASK_FAILED.value, "failed", attempt=record.attempt, payload={"error": str(e)})
            await self._ws_emit("task_failed", task_id, {"error": str(e)})
            await self._dispatch_webhook("task.failed", task_id, {"error": str(e)})
            self.audit_logger.record(
                actor="system",
                action="task_failed",
                resource_type="task",
                resource_id=task_id,
                task_id=task_id,
                metadata={"error": str(e)},
            )
            logger.error("Task failed", task_id=task_id, error=str(e))
            raise

        return record

    # --- Webhook Dispatch ---

    async def _dispatch_webhook(self, event_type: str, task_id: str, data: dict) -> None:
        """Dispatch webhook event asynchronously."""
        try:
            wm = get_webhook_manager()
            await wm.dispatch(event_type, {"task_id": task_id, **data})
        except Exception:  # noqa: BLE001 - webhooks are best-effort
            pass

    # --- Control Methods ---


    async def cancel_task(self, task_id: str) -> dict:
        record = self._tasks.get(task_id)
        if not record:
            raise ValueError(f"Task not found: {task_id}")
        if not record.can_transition("cancelled"):
            return {"success": False, "error": f"Cannot cancel task in state {record.status.value}"}

        record.cancel_event.set()
        record.pause_event.set()

        queue_cancelled = await self.task_queue.cancel_task(task_id)

        if record.status in (TaskStatus.QUEUED, TaskStatus.PENDING):
            record.status = TaskStatus.CANCELLED
            record.updated_at = datetime.now(timezone.utc)

        self.event_store.publish(task_id, TaskEventType.TASK_CANCELLED.value, "cancelled", attempt=record.attempt)
        await self._ws_emit("task_cancelled", task_id, {"queue_cancelled": queue_cancelled})
        self.audit_logger.record(
            actor="system",
            action="task_cancelled",
            resource_type="task",
            resource_id=task_id,
            task_id=task_id,
            metadata={"queue_cancelled": queue_cancelled},
        )
        await self._persist_task_status(task_id, "cancelled")
        await self._persist_audit("system", "task_cancelled", "task", task_id, task_id=task_id)
        self._publish_task_event(task_id, TaskEventType.TASK_CANCELLED.value)
        return {"success": True, "task_id": task_id, "status": record.status.value}

    async def pause_task(self, task_id: str) -> dict:
        record = self._tasks.get(task_id)
        if not record:
            raise ValueError(f"Task not found: {task_id}")
        if not record.can_transition("paused"):
            return {"success": False, "error": f"Cannot pause task in state {record.status.value}"}

        record.pause_event.clear()
        record.status = TaskStatus.PAUSED
        record.updated_at = datetime.now(timezone.utc)
        self.event_store.publish(task_id, TaskEventType.TASK_PAUSED.value, "paused", attempt=record.attempt)
        await self._ws_emit("task_paused", task_id, {})
        self.audit_logger.record(
            actor="system",
            action="task_paused",
            resource_type="task",
            resource_id=task_id,
            task_id=task_id,
        )
        await self._persist_task_status(task_id, "paused")
        await self._persist_audit("system", "task_paused", "task", task_id, task_id=task_id)
        self._publish_task_event(task_id, TaskEventType.TASK_PAUSED.value)
        return {"success": True, "task_id": task_id}

    async def resume_task(self, task_id: str) -> dict:
        record = self._tasks.get(task_id)
        if not record:
            raise ValueError(f"Task not found: {task_id}")
        if not record.can_transition("running"):
            return {"success": False, "error": f"Cannot resume task in state {record.status.value}"}

        record.pause_event.set()
        record.status = TaskStatus.RUNNING
        record.updated_at = datetime.now(timezone.utc)
        self.event_store.publish(task_id, TaskEventType.TASK_RESUMED.value, "running", attempt=record.attempt)
        await self._ws_emit("task_resumed", task_id, {})
        self.audit_logger.record(
            actor="system",
            action="task_resumed",
            resource_type="task",
            resource_id=task_id,
            task_id=task_id,
        )
        await self._persist_task_status(task_id, "paused")
        await self._persist_audit("system", "task_paused", "task", task_id, task_id=task_id)
        self._publish_task_event(task_id, TaskEventType.TASK_PAUSED.value)
        return {"success": True, "task_id": task_id}

    async def retry_task(self, task_id: str) -> dict:
        record = self._tasks.get(task_id)
        if not record:
            raise ValueError(f"Task not found: {task_id}")
        if not record.can_transition("queued"):
            return {"success": False, "error": f"Cannot retry task in state {record.status.value}"}

        record.loop_result = None
        record.error_message = None
        record.updated_at = datetime.now(timezone.utc)

        self.event_store.publish(task_id, TaskEventType.TASK_RETRIED.value, "queued", attempt=record.attempt)
        await self.task_queue.submit(
            task_id,
            self._run_task_internal(task_id, record.max_iterations),
            self,
        )
        await self._ws_emit("task_retried", task_id, {"attempt": record.attempt + 1})
        self.audit_logger.record(
            actor="system",
            action="task_retry",
            resource_type="task",
            resource_id=task_id,
            task_id=task_id,
        )
        await self._persist_audit("system", "task_retry", "task", task_id, task_id=task_id)
        self._publish_task_event(task_id, TaskEventType.TASK_RETRIED.value)
        return {"success": True, "task_id": task_id, "status": record.status.value}

    async def _ws_emit(self, event_type: str, task_id: str, data: dict) -> None:
        if self._ws_broadcast:
            try:
                from app.api.v1.websocket import make_event
                event = make_event(event_type, task_id, data)
                await self._ws_broadcast(task_id, event)
            except Exception:  # noqa: BLE001
                pass


    # ----------------------------------------------------------------
    # Graceful Shutdown
    # ----------------------------------------------------------------

    async def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("Runtime shutdown initiated", instance_id=self.instance_id)
        await self.task_queue.shutdown(timeout=min(self.shutdown_timeout, 10.0))
        if self._event_bridge:
            await self._event_bridge.stop_listener()
        if self._distributed_state:
            try:
                await self._distributed_state.deregister_instance(self.instance_id)
            except Exception:
                pass
        if self._redis_client:
            try:
                await self._redis_client.disconnect()
            except Exception:
                pass
        logger.info("Runtime shutdown complete", instance_id=self.instance_id)

    # --- Query Methods ---


    def get_task(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        return [r.to_dict() for r in self._tasks.values()]

    def get_agents(self) -> list[dict]:
        return self.runtime.list_agents()

    def get_trace(self, task_id: str) -> list[dict]:
        return self.trace_collector.get_trace(task_id)

    def get_metrics(self) -> dict:
        return RuntimeMetrics(self.trace_collector).compute()

    def get_history(self, task_id: str) -> list[dict]:
        return self.history.get_history(task_id)

    def get_task_events(self, task_id: str, since_sequence: int = 0) -> list[dict]:
        events = self.event_store.get_events(task_id, since_sequence=since_sequence)
        return [e.to_dict() for e in events]

    def get_queue_status(self) -> dict:
        return self.task_queue.queue_status()



    @property
    def health_tracker(self):
        return self._health_tracker

    @property
    def event_bridge(self):
        return self._event_bridge


_runtime: AppRuntime | None = None



def get_runtime() -> AppRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AppRuntime()
    return _runtime


def reset_runtime() -> None:
    global _runtime
    _runtime = None