"""
GracefulShutdown & ReadinessProbe - Production readiness and graceful termination.
Phase 4.25: Stop accepting work, drain running tasks, save state, release locks, close connections.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ShutdownPhase(str, Enum):
    """Phases of a graceful shutdown."""
    RUNNING = "running"
    DRAINING = "draining"
    WAITING = "waiting"
    SAVING = "saving"
    RELEASING = "releasing"
    CLOSING = "closing"
    STOPPED = "stopped"


@dataclass
class ShutdownReport:
    """Report produced after graceful shutdown."""
    phase: ShutdownPhase = ShutdownPhase.RUNNING
    tasks_drained: int = 0
    tasks_remaining: int = 0
    state_saved: bool = False
    locks_released: bool = False
    connections_closed: bool = False
    duration_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.value,
            "tasks_drained": self.tasks_drained,
            "tasks_remaining": self.tasks_remaining,
            "state_saved": self.state_saved,
            "locks_released": self.locks_released,
            "connections_closed": self.connections_closed,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
        }


class ReadinessProbe:
    """
    Readiness probe for Kubernetes / Docker healthcheck.

    States:
    - ready: accepting traffic
    - not_ready: draining or stopped
    """

    def __init__(self):
        self._ready = True

    @property
    def is_ready(self) -> bool:
        return self._ready

    def mark_not_ready(self) -> None:
        self._ready = False

    def mark_ready(self) -> None:
        self._ready = True


class GracefulShutdown:
    """
    Orchestrates graceful shutdown for production deployments.

    Flow:
    1. DRAINING  - Stop accepting new tasks
    2. WAITING   - Wait for running tasks to complete
    3. SAVING    - Persist runtime state
    4. RELEASING - Release distributed locks, step down as leader
    5. CLOSING   - Close DB connections, Redis, event loops
    6. STOPPED   - Exit
    """

    def __init__(
        self,
        runtime=None,
        leader_election=None,
        cluster_manager=None,
        readiness_probe: ReadinessProbe | None = None,
        drain_timeout: float = 30.0,
    ):
        self._runtime = runtime
        self._leader = leader_election
        self._cluster = cluster_manager
        self._probe = readiness_probe or ReadinessProbe()
        self._drain_timeout = drain_timeout
        self._phase = ShutdownPhase.RUNNING
        self._report = ShutdownReport()

    @property
    def phase(self) -> ShutdownPhase:
        return self._phase

    @property
    def report(self) -> ShutdownReport:
        return self._report

    async def shutdown(self) -> ShutdownReport:
        """Execute the full graceful shutdown sequence."""
        import time
        start = time.monotonic()

        try:
            # Phase 1: Drain
            await self._drain()
            # Phase 2: Wait
            await self._wait_for_tasks()
            # Phase 3: Save
            await self._save_state()
            # Phase 4: Release
            await self._release_locks()
            # Phase 5: Close
            await self._close_connections()
        except Exception as e:
            self._report.errors.append(str(e))
            logger.error("Shutdown error", error=str(e))

        self._phase = ShutdownPhase.STOPPED
        self._report.duration_ms = (time.monotonic() - start) * 1000
        logger.info("Graceful shutdown complete", **self._report.to_dict())
        return self._report

    # -- Phases --

    async def _drain(self) -> None:
        """Stop accepting new work."""
        self._phase = ShutdownPhase.DRAINING
        self._probe.mark_not_ready()
        logger.info("Draining - no longer accepting tasks")

        if self._runtime:
            self._runtime._shutting_down = True
            if hasattr(self._runtime, "task_queue"):
                await self._runtime.task_queue.pause()

    async def _wait_for_tasks(self) -> None:
        """Wait for running tasks to complete (with timeout)."""
        self._phase = ShutdownPhase.WAITING

        if not self._runtime:
            return

        deadline = asyncio.get_event_loop().time() + self._drain_timeout
        while asyncio.get_event_loop().time() < deadline:
            running = self._runtime.task_queue.queue_status().get("running", 0)
            if running == 0:
                break
            self._report.tasks_remaining = running
            await asyncio.sleep(0.5)

        self._report.tasks_drained = self._report.tasks_remaining
        logger.info("Tasks drained", remaining=self._report.tasks_remaining)

    async def _save_state(self) -> None:
        """Persist runtime state before shutdown."""
        self._phase = ShutdownPhase.SAVING
        try:
            if self._runtime and hasattr(self._runtime, "shutdown"):
                await self._runtime.shutdown()
            self._report.state_saved = True
        except Exception as e:
            self._report.errors.append(f"State save failed: {e}")

    async def _release_locks(self) -> None:
        """Release distributed locks and cluster membership."""
        self._phase = ShutdownPhase.RELEASING
        try:
            if self._leader:
                await self._leader.step_down()
            if self._cluster:
                await self._cluster.deregister()
            self._report.locks_released = True
        except Exception as e:
            self._report.errors.append(f"Lock release failed: {e}")

    async def _close_connections(self) -> None:
        """Close all external connections."""
        self._phase = ShutdownPhase.CLOSING
        try:
            if self._runtime:
                if hasattr(self._runtime, "_redis_client") and self._runtime._redis_client:
                    await self._runtime._redis_client.disconnect()
            self._report.connections_closed = True
        except Exception as e:
            self._report.errors.append(f"Connection close failed: {e}")