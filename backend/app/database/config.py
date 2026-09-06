"""
Database persistence configuration.
Phase 4.18: Environment-driven settings for production PostgreSQL deployment.
"""

from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database connection settings, read from environment variables."""
    database_url: str = "postgresql+asyncpg://workbench:workbench_dev_2026@localhost:5432/ai_workbench"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    database_pool_pre_ping: bool = True
    database_connect_timeout: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


_db_settings: DatabaseSettings | None = None


def get_db_settings() -> DatabaseSettings:
    global _db_settings
    if _db_settings is None:
        _db_settings = DatabaseSettings()
    return _db_settings


def reset_db_settings() -> None:
    global _db_settings
    _db_settings = None