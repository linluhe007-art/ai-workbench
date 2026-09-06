"""
Database infrastructure - SQLAlchemy 2.0 async engine, session, and base.
Phase 4.17: Refactored with clear session management and ORM models.
Phase 4.18: Health checks, database info, environment-driven config.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from app.database.config import get_db_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

settings = get_settings()
db_config = get_db_settings()

engine = create_async_engine(
    db_config.database_url or settings.database_url,
    echo=db_config.database_echo,
    pool_size=db_config.database_pool_size,
    max_overflow=db_config.database_max_overflow,
    pool_pre_ping=db_config.database_pool_pre_ping,
    connect_args={"timeout": db_config.database_connect_timeout},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_session() -> AsyncSession:
    """Get a new async database session (for dependency injection)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:  # noqa: BLE001
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncSession:
    """Alias for get_session (backward compatible)."""
    async for session in get_session():
        yield session


async def init_db() -> None:
    """Create all tables if they don't exist (auto-migration for dev)."""
    import app.database.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")


async def check_db() -> bool:
    """Check database connectivity."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


async def get_database_info() -> dict:
    """Get database connection and version information."""
    info = {
        "connected": False,
        "database": "unknown",
        "dialect": "postgresql",
        "version": "unknown",
    }
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            row = result.fetchone()
            if row:
                info["version"] = row[0]
            info["connected"] = True
            info["database"] = settings.postgres_db or "ai_workbench"
    except Exception:  # noqa: BLE001
        pass
    return info


async def check_and_report_db() -> dict:
    """Comprehensive health check returning structured status."""
    connected = await check_db()
    info = await get_database_info() if connected else {"connected": False}
    return {
        **info,
        "status": "healthy" if connected else "unavailable",
        "pool_size": db_config.database_pool_size,
    }