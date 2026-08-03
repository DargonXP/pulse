from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UpWise API"
    environment: str = "development"

    database_url: str = "sqlite:///./upwise.db"  # In production (Render), override via DATABASE_URL env var, e.g. sqlite:////var/data/upwise.db

    secret_key: str = "dev-secret-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    cors_origins: str = "*"

    seed_on_startup: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
