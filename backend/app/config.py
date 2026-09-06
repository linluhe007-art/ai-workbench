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

    # Phase 4.19: Runtime persistence and instance settings
    persistence_enabled: bool = True
    redis_enabled: bool = True
    runtime_instance_id: str = ""
    shutdown_timeout_seconds: int = 30


    # JWT

    jwt_secret_key: str = "change-me-to-a-random-secret-in-production"

    @property
    def effective_jwt_secret(self) -> str:
        return self.auth_jwt_secret or self.jwt_secret_key

    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15

    jwt_refresh_token_expire_days: int = 7

    # Phase 4.20: Auth security hardening
    auth_jwt_secret: str = ""
    auth_access_token_expire_minutes: int = 15
    auth_refresh_token_expire_days: int = 7
    auth_allow_dev_user_header: bool = True


    
    # Phase Beta-Search: Search infrastructure
    search_provider: str = "mock"
    search_api_key: str = ""
    search_max_results: int = 10
    search_timeout_seconds: int = 30
    # Phase Beta-LLM: LLM provider configuration
    llm_provider: str = "deepseek"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: int = 60
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4000
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    # Memory — Obsidian 知识库路径（可选，可通过 OBSIDIAN_VAULT_PATH 覆盖）
    obsidian_vault_path: str = r"D:\Obsidian仓库\个人知识库"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
