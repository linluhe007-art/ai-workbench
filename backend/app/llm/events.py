"""LLM event publishing helpers (Phase Beta-LLM)."""

from __future__ import annotations

from typing import Any


def publish_llm_event(event_type: str, data: dict[str, Any] | None = None, task_id: str | None = None) -> None:
    """Publish an LLM lifecycle event without failing the main flow."""
    try:
        payload = dict(data or {})
        if task_id:
            try:
                from app.runtime.manager import get_runtime
                runtime = get_runtime()
                runtime.event_store.publish(task_id, event_type, "running", payload=payload)
            except Exception:
                pass
        try:
            from app.api.v1.websocket import get_ws_manager, make_event
            event = make_event(event_type, task_id or "system", payload)
            if task_id:
                import asyncio
                asyncio.create_task(get_ws_manager().broadcast(task_id, event))
        except Exception:
            pass
    except Exception:
        pass
