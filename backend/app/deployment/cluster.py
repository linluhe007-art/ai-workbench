"""
ClusterManager - Multi-instance discovery and health tracking.
Phase 4.25: Production deployment - instance registration, heartbeat, discovery.
"""
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ClusterInstance:
    """Represents a single backend instance in the cluster."""
    instance_id: str
    host: str = "localhost"
    port: int = 8000
    status: str = "starting"
    role: str = "worker"  # leader / worker
    started_at: str = ""
    last_heartbeat: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "host": self.host,
            "port": self.port,
            "status": self.status,
            "role": self.role,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "metadata": self.metadata,
        }


class ClusterManager:
    """
    Manages cluster membership using Redis for discovery.

    Features:
    - Instance registration with TTL heartbeat
    - Instance discovery (list all peers)
    - Leader identification
    - Health check aggregation
    - In-memory fallback when Redis unavailable
    """

    HEARTBEAT_TTL = 30  # seconds
    CLUSTER_KEY = "cluster:instances"
    LEADER_KEY = "cluster:leader"

    def __init__(self, redis_client=None, instance_id: str = ""):
        self._redis = redis_client
        self.instance_id = instance_id or f"inst-{uuid.uuid4().hex[:8]}"
        self._instances: dict[str, ClusterInstance] = {}
        self._started_at = datetime.now(timezone.utc).isoformat()

    # -- Registration --

    async def register(self, host: str = "localhost", port: int = 8000) -> ClusterInstance:
        """Register this instance in the cluster."""
        inst = ClusterInstance(
            instance_id=self.instance_id,
            host=host,
            port=port,
            status="healthy",
            role="worker",
            started_at=self._started_at,
            last_heartbeat=datetime.now(timezone.utc).isoformat(),
        )

        if self._redis:
            try:
                key = f"{self.CLUSTER_KEY}:{self.instance_id}"
                await self._redis.client.set(key, str(port), ex=self.HEARTBEAT_TTL)
                logger.info("Instance registered in Redis", instance_id=self.instance_id)
            except Exception as e:
                logger.warning("Redis registration failed, using in-memory mode", error=str(e))
                self._redis = None

        self._instances[self.instance_id] = inst
        return inst

    async def deregister(self) -> None:
        """Remove this instance from the cluster (on shutdown)."""
        if self._redis:
            try:
                await self._redis.client.delete(f"{self.CLUSTER_KEY}:{self.instance_id}")
            except Exception:
                pass
        self._instances.pop(self.instance_id, None)

    # -- Heartbeat --

    async def heartbeat(self) -> None:
        """Send a heartbeat to keep instance alive."""
        now = datetime.now(timezone.utc).isoformat()
        if self._redis:
            try:
                key = f"{self.CLUSTER_KEY}:{self.instance_id}"
                inst = self._instances.get(self.instance_id)
                port = inst.port if inst else 8000
                await self._redis.client.set(key, str(port), ex=self.HEARTBEAT_TTL)
            except Exception:
                pass

        if self.instance_id in self._instances:
            self._instances[self.instance_id].last_heartbeat = now

    # -- Discovery --

    async def discover(self) -> list[ClusterInstance]:
        """Discover all instances in the cluster."""
        results: list[ClusterInstance] = []

        if self._redis:
            try:
                keys = await self._redis.client.keys(f"{self.CLUSTER_KEY}:*")
                for key in keys:
                    instance_id = key.decode() if isinstance(key, bytes) else key
                    instance_id = instance_id.split(":", 2)[-1]
                    port_val = await self._redis.client.get(key)
                    port = int(port_val) if port_val else 8000

                    inst = ClusterInstance(
                        instance_id=instance_id,
                        port=port,
                        status="healthy",
                        last_heartbeat=datetime.now(timezone.utc).isoformat(),
                    )
                    results.append(inst)
            except Exception as e:
                logger.warning("Redis discovery failed", error=str(e))

        # Merge with in-memory
        for inst in self._instances.values():
            if inst.instance_id not in {r.instance_id for r in results}:
                results.append(inst)

        return results

    # -- Leader --

    async def get_leader(self) -> ClusterInstance | None:
        """Get the current leader instance."""
        if self._redis:
            try:
                leader_id = await self._redis.client.get(self.LEADER_KEY)
                if leader_id:
                    for inst in await self.discover():
                        if inst.instance_id == leader_id:
                            inst.role = "leader"
                            return inst
            except Exception:
                pass
        return None

    async def set_leader(self, instance_id: str | None) -> None:
        """Set the leader instance."""
        if self._redis:
            try:
                if instance_id:
                    await self._redis.client.set(self.LEADER_KEY, instance_id, ex=60)
                else:
                    await self._redis.client.delete(self.LEADER_KEY)
            except Exception:
                pass

    # -- Health --

    async def cluster_health(self) -> dict:
        """Aggregate health status of all instances."""
        instances = await self.discover()
        leader = await self.get_leader()

        return {
            "total_instances": len(instances),
            "healthy_instances": len([i for i in instances if i.status == "healthy"]),
            "leader": leader.to_dict() if leader else None,
            "instances": [i.to_dict() for i in instances],
            "self": self.instance_id,
        }

    # -- Heartbeat loop --

    async def start_heartbeat_loop(self, interval: float = 10.0) -> None:
        """Start a background heartbeat loop."""
        async def _loop():
            while True:
                await self.heartbeat()
                await asyncio.sleep(interval)
        asyncio.create_task(_loop())