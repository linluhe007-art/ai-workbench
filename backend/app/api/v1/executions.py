"""
Executions API — 执行历史与 Trace 查询。

GET /api/v1/executions/metrics    — 运行时指标
GET /api/v1/executions/trace/all  — 所有 Trace 事件
"""

from fastapi import APIRouter

from app.runtime.manager import get_runtime
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("/metrics")
async def get_metrics():
    """获取运行时执行指标"""
    runtime = get_runtime()
    return runtime.get_metrics()


@router.get("/trace/all")
async def get_all_traces():
    """获取所有 Trace 事件"""
    runtime = get_runtime()
    events = [e.to_dict() for e in runtime.trace_collector._events]
    return {
        "events": events,
        "total": len(events),
    }


@router.get("/trace/errors")
async def get_trace_errors():
    """获取所有错误 Trace 事件"""
    runtime = get_runtime()
    errors = runtime.trace_collector.get_errors()
    return {
        "errors": errors,
        "total": len(errors),
    }


@router.get("/trace/component/{component}")
async def get_traces_by_component(component: str):
    """按组件过滤 Trace 事件"""
    runtime = get_runtime()
    events = runtime.trace_collector.get_by_component(component)
    return {
        "component": component,
        "events": events,
        "total": len(events),
    }