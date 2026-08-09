import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.database.redis import get_redis

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@router.get("/db")
async def db_health(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "service": "postgresql"}
    except Exception as e:  # noqa: BLE001 — health check error reporting
        return {"status": "unhealthy", "service": "postgresql", "error": str(e)}


@router.get("/redis")
async def redis_health(r: redis.Redis = Depends(get_redis)):
    try:
        await r.ping()
        return {"status": "healthy", "service": "redis"}
    except Exception as e:  # noqa: BLE001 — health check error reporting
        return {"status": "unhealthy", "service": "redis", "error": str(e)}


@router.get("/all")
async def full_health(db: AsyncSession = Depends(get_db), r: redis.Redis = Depends(get_redis)):
    services = {}

    try:
        await db.execute(text("SELECT 1"))
        services["postgresql"] = "healthy"
    except Exception as e:  # noqa: BLE001 — health check error reporting
        services["postgresql"] = f"unhealthy: {e}"

    try:
        await r.ping()
        services["redis"] = "healthy"
    except Exception as e:  # noqa: BLE001 — health check error reporting
        services["redis"] = f"unhealthy: {e}"

    all_ok = all(v == "healthy" for v in services.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "services": services,
    }