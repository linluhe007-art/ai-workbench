"""
WebSocket API - real-time task events with replay support.
Phase 4.12: reconnect, replay, heartbeat, sequence.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """WebSocket connection manager with replay support."""

    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(task_id, []).append(ws)
        logger.info("WS connected", task_id=task_id, total=len(self._connections[task_id]))

    def disconnect(self, task_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(task_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(task_id, None)
        logger.info("WS disconnected", task_id=task_id)

    async def broadcast(self, task_id: str, event: dict) -> None:
        conns = self._connections.get(task_id, [])
        if not conns:
            return
        message = json.dumps(event, ensure_ascii=False, default=str)
        dead = []
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(task_id, ws)

    async def broadcast_all(self, event: dict) -> None:
        for task_id in list(self._connections.keys()):
            await self.broadcast(task_id, event)

    def subscriber_count(self, task_id: str) -> int:
        return len(self._connections.get(task_id, []))

    @property
    def total_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


_manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    return _manager


def reset_ws_manager() -> None:
    global _manager
    _manager = ConnectionManager()


def make_event(event_type: str, task_id: str, data: dict | None = None) -> dict:
    return {
        "event": event_type,
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data or {},
    }


@router.websocket("/ws/tasks/{task_id}")
async def task_websocket(
    ws: WebSocket,
    task_id: str,
    since_sequence: int = Query(default=0, description="Replay events since this sequence"),
):
    """
    Task event subscription with replay support.
    Client can pass ?since_sequence=N to replay missed events on reconnect.
    """
    manager = get_ws_manager()
    await manager.connect(task_id, ws)

    # Send connection confirmation with last_sequence
    from app.runtime.manager import get_runtime
    runtime = get_runtime()
    last_seq = runtime.event_store.get_last_sequence(task_id)

    await ws.send_text(json.dumps(
        make_event("connected", task_id, {
            "message": "Subscribed to task events",
            "last_sequence": last_seq,
        }),
        ensure_ascii=False,
    ))

    # Replay missed events if since_sequence > 0
    if since_sequence > 0:
        await ws.send_text(json.dumps(
            make_event("event_replay_started", task_id, {"since_sequence": since_sequence}),
            ensure_ascii=False,
        ))
        missed = runtime.get_task_events(task_id, since_sequence=since_sequence)
        for ev in missed:
            await ws.send_text(json.dumps(
                make_event("event_replayed", task_id, ev),
                ensure_ascii=False,
            ))
        await ws.send_text(json.dumps(
            make_event("event_replay_completed", task_id, {"replayed": len(missed)}),
            ensure_ascii=False,
        ))

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text(json.dumps(
                    make_event("pong", task_id, {"sequence": last_seq}),
                    ensure_ascii=False,
                ))
    except WebSocketDisconnect:
        manager.disconnect(task_id, ws)
    except Exception:  # noqa: BLE001
        manager.disconnect(task_id, ws)