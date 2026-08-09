import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

redis_client = redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> redis.Redis:
    return redis_client


async def check_redis() -> bool:
    try:
        await redis_client.ping()
        return True
    except Exception:  # noqa: BLE001 — redis ping failure is non-critical
        return False