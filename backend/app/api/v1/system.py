"""
System API - health, readiness, cluster, instance info, and graceful shutdown.
Phase 4.19: Production-ready health endpoints with persistence status.
Phase 4.25: Cluster endpoint for HA deployments.
"""

import asyncio
import os
import signal
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/system", tags=["system"])

_shutdown_initiated = False


@router.get("/health")
async def system_health():
    """Basic health check - always returns healthy if running."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "ai-workbench",
    }


@router.get("/readiness")
async def system_readiness():
    """
    Readiness probe - checks if runtime is fully initialized.
    Includes database and Redis status.
    """
    try:
        from app.runtime.manager import get_runtime
        runtime = get_runtime()

        if hasattr(runtime, 'health_tracker') and runtime.health_tracker:
            status = runtime.health_tracker.get_status()
            is_ready = status.status in ("healthy", "running", "degraded")
            return {
                "ready": is_ready,
                "status": status.status,
                "persistence": status.persistence_status,
                "redis": status.redis_status,
                "instance_id": status.instance_id,
                "uptime_seconds": status.uptime_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "ready": True,
            "status": "running",
            "persistence": "unknown",
            "redis": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.warning("Readiness check failed", error=str(e)[:100])
        return {
            "ready": False,
            "status": "error",
            "error": str(e)[:200],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/info")
async def system_info():
    """Get detailed system information including persistence status."""
    try:
        from app.runtime.manager import get_runtime
        runtime = get_runtime()

        info = {
            "instance_id": runtime.instance_id,
            "started_at": runtime.started_at,
            "status": "running",
        }

        if hasattr(runtime, 'health_tracker') and runtime.health_tracker:
            status = runtime.health_tracker.get_status()
            info["health"] = status.to_dict()

        info["active_tasks"] = runtime.task_queue.running_count
        info["queued_tasks"] = runtime.task_queue.queued_count
        info["total_tasks"] = len(runtime._tasks)

        metrics = runtime.get_metrics()
        if metrics:
            info["metrics"] = metrics

        return info
    except Exception as e:
        return {
            "instance_id": "unknown",
            "status": "error",
            "error": str(e)[:200],
        }


@router.get("/cluster")
async def system_cluster():
    """
    Cluster status - instances, leader, health.
    Phase 4.25: Production deployment & HA cluster view.
    """
    try:
        from app.runtime.manager import get_runtime
        runtime = get_runtime()

        instances = []
        self_info = {
            "instance_id": runtime.instance_id,
            "status": "healthy",
            "role": "leader" if not runtime.redis_enabled else "worker",
            "started_at": runtime.started_at,
        }
        instances.append(self_info)

        if runtime.redis_enabled and hasattr(runtime, '_distributed_state') and runtime._distributed_state:
            try:
                peers = await runtime._distributed_state.list_instances()
                for peer in peers:
                    if peer.get("instance_id") != runtime.instance_id:
                        instances.append({
                            "instance_id": peer.get("instance_id", ""),
                            "status": "healthy",
                            "role": "worker",
                            "started_at": peer.get("started_at", ""),
                        })
            except Exception:
                pass

        return {
            "instances": instances,
            "total": len(instances),
            "leader": next((i["instance_id"] for i in instances if i["role"] == "leader"), None),
            "self": runtime.instance_id,
            "health": {
                "persistence": "healthy" if runtime.persistence_enabled else "disabled",
                "redis": "healthy" if runtime.redis_enabled else "disabled",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.warning("Cluster endpoint error", error=str(e))
        return {
            "instances": [],
            "total": 0,
            "leader": None,
            "error": str(e)[:200],
        }


@router.post("/shutdown")
async def graceful_shutdown():
    """Initiate graceful shutdown."""
    global _shutdown_initiated
    if _shutdown_initiated:
        return {"status": "shutdown_already_in_progress"}

    _shutdown_initiated = True
    logger.info("Graceful shutdown initiated via API")

    try:
        from app.runtime.manager import get_runtime
        runtime = get_runtime()
        await runtime.shutdown()
    except Exception as e:
        logger.error("Shutdown error", error=str(e))

    async def _delayed_shutdown():
        await asyncio.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(_delayed_shutdown())

    return {
        "status": "shutting_down",
        "message": "Graceful shutdown initiated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics")
async def system_metrics():
    """Get runtime metrics."""
    try:
        from app.runtime.manager import get_runtime
        runtime = get_runtime()
        return {
            "metrics": runtime.get_metrics(),
            "queue": runtime.get_queue_status(),
        }
    except Exception as e:
        return {"error": str(e)[:200]}