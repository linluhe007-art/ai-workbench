"""Self Improvement API - Phase 5.8"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.improvement.analyzer import get_performance_analyzer
from app.improvement.strategy import get_strategy_engine
from app.improvement.optimizer import get_optimization_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/improvement", tags=["improvement"])


class ApplyRequest(BaseModel):
    recommendation_ids: list[str] = []


@router.get("/report")
async def get_improvement_report():
    """Analyze performance and generate improvement recommendations."""
    analyzer = get_performance_analyzer()
    strategy_engine = get_strategy_engine()

    # Analyze
    report = await analyzer.analyze()
    # Generate strategies
    plan = strategy_engine.generate(report)

    return {
        "success": True,
        "analysis": report.to_dict(),
        "strategy_plan": plan.to_dict(),
    }


@router.post("/apply")
async def apply_improvement(req: ApplyRequest):
    """Apply selected or all recommendations."""
    analyzer = get_performance_analyzer()
    strategy_engine = get_strategy_engine()
    optimizer = get_optimization_engine()

    report = await analyzer.analyze()
    plan = strategy_engine.generate(report)

    if req.recommendation_ids:
        recs = [r for r in plan.recommendations if r.id in req.recommendation_ids]
    else:
        recs = plan.recommendations

    records = []
    for rec in recs:
        records.append(optimizer.apply(rec).to_dict())

    return {
        "success": True,
        "applied": len(records),
        "records": records,
    }


@router.get("/history")
async def get_improvement_history():
    """Get history of applied optimizations."""
    optimizer = get_optimization_engine()
    records = optimizer.list_records()
    stats = optimizer.get_stats()
    return {
        "success": True,
        "records": records,
        "stats": stats,
    }


@router.post("/revert/{record_id}")
async def revert_improvement(record_id: str):
    """Revert a previously applied optimization."""
    optimizer = get_optimization_engine()
    ok = optimizer.revert(record_id)
    return {
        "success": ok,
        "record_id": record_id,
        "message": "Reverted" if ok else "Record not found or already reverted",
    }
