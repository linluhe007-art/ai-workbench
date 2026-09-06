"""
Metrics API - runtime observability endpoints.
Phase 4.21: Metrics, task stats, agent stats.
"""

import os
import time
import psutil
from fastapi import APIRouter

from app.observability.metrics_collector import get_metrics_collector
from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])

_start_time = time.time()


def _get_cpu_usage() -> float:
    try:
        return psutil.cpu_percent(interval=0.1)
    except Exception:
        return 0.0


def _get_memory_usage() -> dict:
    try:
        mem = psutil.virtual_memory()
        process = psutil.Process(os.getpid())
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent,
            "process_mb": round(process.memory_info().rss / (1024**2), 1),
        }
    except Exception:
        return {"total_gb": 0, "available_gb": 0, "percent": 0, "process_mb": 0}


@router.get("")
async def get_metrics():
    """Get comprehensive runtime metrics."""
    runtime = get_runtime()
    collector = get_metrics_collector()
    queue = runtime.get_queue_status()

    return {
        "cpu": {
            "percent": _get_cpu_usage(),
        },
        "memory": _get_memory_usage(),
        "runtime": {
            "instance_id": runtime.instance_id,
            "uptime_seconds": time.time() - _start_time,
            "status": runtime.health_tracker.status if runtime.health_tracker else "unknown",
            "persistence_enabled": runtime.persistence_enabled,
            "redis_enabled": runtime.redis_enabled,
        },
        "tasks": {
            "total": len(runtime._tasks),
            "created": collector.get_counter("tasks_created_total"),
            "completed": collector.get_counter("tasks_completed_total"),
            "failed": collector.get_counter("tasks_failed_total"),
            "timeout": collector.get_counter("tasks_timeout_total"),
            "cancelled": collector.get_counter("tasks_cancelled_total"),
        },
        "queue": {
            "running": queue.get("running", 0),
            "queued": queue.get("queued", 0),
            "max_concurrent": queue.get("max_concurrent", 3),
        },
        "agents": {
            "total_executions": collector.get_counter("agent_execute_total"),
            "success_rate": _safe_rate(
                collector.get_counter("agent_execute_total"),
                collector.get_counter("agent_execute_total") - collector.get_counter("agent_error_total"),
            ),
            "latency": collector.get_histogram_stats("agent_latency_ms"),
        },
    }


def _safe_rate(total: float, success: float) -> float:
    if total == 0:
        return 0.0
    return round(success / total, 3)


@router.get("/tasks")
async def get_task_metrics():
    """Get task-specific metrics."""
    collector = get_metrics_collector()
    created = collector.get_counter("tasks_created_total")
    completed = collector.get_counter("tasks_completed_total")
    failed = collector.get_counter("tasks_failed_total")
    timeout = collector.get_counter("tasks_timeout_total")
    cancelled = collector.get_counter("tasks_cancelled_total")
    total = created

    return {
        "total": total,
        "completed": completed,
        "failed": failed,
        "timeout": timeout,
        "cancelled": cancelled,
        "success_rate": _safe_rate(total, completed),
        "failure_rate": _safe_rate(total, failed + timeout),
        "average_duration_ms": collector.get_histogram_stats("task_duration_ms").get("avg", 0),
    }


@router.get("/agents")
async def get_agent_metrics():
    """Get agent-specific metrics."""
    runtime = get_runtime()
    collector = get_metrics_collector()
    agents = runtime.get_agents()

    agent_stats = []
    for agent in agents:
        agent_id = agent.get("name", "") if isinstance(agent, dict) else getattr(agent, "name", "")
        if not agent_id:
            continue
        agent_stats.append({
            "agent_id": agent_id,
            "executions": collector.get_counter("agent_execute_total", {"agent": agent_id}),
            "errors": collector.get_counter("agent_error_total", {"agent": agent_id}),
            "latency": collector.get_histogram_stats("agent_latency_ms", {"agent": agent_id}),
        })

    return {
        "total_executions": collector.get_counter("agent_execute_total"),
        "agents": agent_stats,
    }
