from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads ../.env (repo root) in local dev; real env vars win in Docker.
    model_config = SettingsConfigDict(env_file="../.env", env_prefix="APP_", extra="ignore")

    app_name: str = "Delta"
    database_url: str = "sqlite+aiosqlite:///../data/app.db"
    encryption_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: float = Field(default=90, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=8)
    llm_validation_retries: int = Field(default=2, ge=0, le=8)


settings = Settings()
