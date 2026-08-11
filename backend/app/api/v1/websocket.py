"""
WebSocket API — 实时任务推送。

WS /api/v1/ws/tasks/{task_id}  — 订阅任务实时事件

事件类型：
- task_started     — 任务开始
- agent_started    — Agent 开始执行
- agent_finished   — Agent 执行完成
- step_completed   — 步骤完成
- evaluation_updated — 评估更新
- task_completed   — 任务完成
- task_failed      — 任务失败
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """
    WebSocket 连接管理器。
    
    按 task_id 管理订阅者，支持广播和单播。
    """

    def __init__(self):
        # task_id -> list[WebSocket]
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, ws: WebSocket) -> None:
        """接受并注册 WebSocket 连接"""
        await ws.accept()
        self._connections.setdefault(task_id, []).append(ws)
        logger.info("WebSocket connected", task_id=task_id, total=len(self._connections[task_id]))

    def disconnect(self, task_id: str, ws: WebSocket) -> None:
        """移除 WebSocket 连接"""
        conns = self._connections.get(task_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(task_id, None)
        logger.info("WebSocket disconnected", task_id=task_id)

    async def broadcast(self, task_id: str, event: dict) -> None:
        """
        向指定 task_id 的所有订阅者广播事件。
        自动清理断开的连接。
        """
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
        """向所有连接广播"""
        for task_id in list(self._connections.keys()):
            await self.broadcast(task_id, event)

    def subscriber_count(self, task_id: str) -> int:
        """获取指定 task_id 的订阅者数量"""
        return len(self._connections.get(task_id, []))

    @property
    def total_connections(self) -> int:
        """获取总连接数"""
        return sum(len(conns) for conns in self._connections.values())


# 全局连接管理器
_manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    """获取全局 WebSocket 连接管理器"""
    return _manager


def reset_ws_manager() -> None:
    """重置连接管理器（仅用于测试）"""
    global _manager
    _manager = ConnectionManager()


def make_event(event_type: str, task_id: str, data: dict | None = None) -> dict:
    """构建标准事件消息"""
    return {
        "event": event_type,
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data or {},
    }


@router.websocket("/ws/tasks/{task_id}")
async def task_websocket(ws: WebSocket, task_id: str):
    """
    任务实时事件订阅。
    
    连接后自动推送任务状态变化。
    
    事件格式：
    {
        "event": "task_started",
        "task_id": "task-xxx",
        "timestamp": "2026-...",
        "data": { ... }
    }
    """
    manager = get_ws_manager()
    await manager.connect(task_id, ws)

    # 发送连接确认
    await ws.send_text(json.dumps(
        make_event("connected", task_id, {"message": "Subscribed to task events"}),
        ensure_ascii=False,
    ))

    try:
        while True:
            # 保持连接，等待客户端消息（心跳或命令）
            data = await ws.receive_text()
            # 支持心跳
            if data == "ping":
                await ws.send_text(json.dumps(
                    make_event("pong", task_id),
                    ensure_ascii=False,
                ))
    except WebSocketDisconnect:
        manager.disconnect(task_id, ws)
    except Exception:  # noqa: BLE001
        manager.disconnect(task_id, ws)