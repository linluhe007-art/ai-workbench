"""Analytics API - Phase 5.11"""
from fastapi import APIRouter

from app.analytics.ai_metrics import get_ai_usage_tracker

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/ai-usage")
async def get_ai_usage(limit: int = 100, offset: int = 0):
    tracker = get_ai_usage_tracker()
    records = tracker.get_records(limit=limit, offset=offset)
    return {"success": True, "records": records, "total": len(records)}


@router.get("/ai-summary")
async def get_ai_summary():
    tracker = get_ai_usage_tracker()
    summary = tracker.get_summary()
    return {"success": True, "summary": summary}
