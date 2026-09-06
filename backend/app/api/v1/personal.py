"""Personal Dashboard API - Phase 5.7"""
from fastapi import APIRouter

from app.analytics.metrics import PersonalMetrics, get_personal_metrics_collector
from app.analytics.insight import AIInsightGenerator, get_insight_generator
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/personal", tags=["personal"])

_insight_gen: AIInsightGenerator | None = None


def _get_insight_gen() -> AIInsightGenerator:
    global _insight_gen
    if _insight_gen is None:
        _insight_gen = get_insight_generator()
    return _insight_gen


@router.get("/dashboard")
async def get_personal_dashboard():
    """Get personal AI dashboard with metrics, insights and daily summary."""
    collector = get_personal_metrics_collector()

    # Collect metrics from subsystems
    metrics = await collector.collect()

    # Generate insights
    insight_gen = _get_insight_gen()
    insights = insight_gen.generate(metrics)

    # Build daily summary
    summary = _build_daily_summary(metrics)

    return {
        "success": True,
        "metrics": metrics.to_dict(),
        "insights": [i.to_dict() for i in insights],
        "daily_summary": summary,
    }


def _build_daily_summary(metrics: PersonalMetrics) -> dict:
    """Build a human-readable daily summary."""
    lines = []

    if metrics.tasks_today > 0:
        lines.append(
            f"今天共创建 {metrics.tasks_today} 个任务，"
            f"完成 {metrics.tasks_completed_today} 个，"
            f"失败 {metrics.tasks_failed_today} 个。"
        )
    else:
        lines.append("今天还没有任务，随时可以开始！")

    if metrics.success_rate > 0:
        lines.append(f"任务成功率：{metrics.success_rate*100:.1f}%。")

    if metrics.agents_active > 0:
        lines.append(f"当前 {metrics.agents_active}/{metrics.agents_total} 个 Agent 活跃中。")

    if metrics.knowledge_items_added > 0:
        lines.append(f"今天新增 {metrics.knowledge_items_added} 条知识。")

    return {
        "text": " ".join(lines),
        "lines": lines,
        "mood": "productive" if metrics.tasks_completed_today > 0 else "idle",
    }
