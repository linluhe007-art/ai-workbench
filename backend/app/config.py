from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

# Environments where the shipped placeholder secret is tolerated.
NON_PRODUCTION_ENVS = {"development", "dev", "local", "test", "testing", "ci"}

# Values that ship in the repository and therefore must never sign real tokens.
PLACEHOLDER_JWT_SECRETS = {
    "",
    "change-me-to-a-random-secret-in-production",
    "changeme",
    "change_me_local_dev_only",
    "secret",
    "your-secret-key",
}

MIN_JWT_SECRET_LENGTH = 32


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
    postgres_password: str = "change_me_local_dev_only"
    postgres_db: str = "ai_workbench"
    database_url: str = "postgresql+asyncpg://workbench:change_me_local_dev_only@localhost:5432/ai_workbench"

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
    auth_allow_dev_user_header: bool = False


    
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
    # Memory — Obsidian 知识库路径（可选，通过 OBSIDIAN_VAULT_PATH 环境变量指定）
    obsidian_vault_path: str = r"/path/to/your/obsidian/vault"

    @model_validator(mode="after")
    def _refuse_placeholder_jwt_secret(self) -> "Settings":
        """Fail fast rather than sign tokens with a secret that is public in the repo."""
        env = (self.app_env or "").strip().lower()
        if env in NON_PRODUCTION_ENVS:
            return self
        secret = (self.effective_jwt_secret or "").strip()
        if secret.lower() in PLACEHOLDER_JWT_SECRETS or len(secret) < MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY is unset, too short (<{MIN_JWT_SECRET_LENGTH} chars) or still a "
                f"placeholder value shipped in the repository, while APP_ENV={self.app_env!r}. "
                "Refusing to start, because such a secret lets anyone forge an admin token. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))" '
                "and set it via JWT_SECRET_KEY (or AUTH_JWT_SECRET)."
            )
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
