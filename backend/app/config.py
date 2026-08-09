from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "AI-Workbench"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "workbench"
    postgres_password: str = "workbench_dev_2026"
    postgres_db: str = "ai_workbench"
    database_url: str = "postgresql+asyncpg://workbench:workbench_dev_2026@localhost:5432/ai_workbench"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str = "change-me-to-a-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Memory — Obsidian 知识库路径
    obsidian_vault_path: str = r"D:\Obsidian仓库\个人知识库"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()