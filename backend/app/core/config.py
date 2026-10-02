from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import default_database_url, get_data_directory


class Settings(BaseSettings):
    # Reads ../.env (repo root) in local dev; real env vars win in packaged apps.
    model_config = SettingsConfigDict(env_file="../.env", env_prefix="APP_", extra="ignore")

    app_name: str = "Delta"
    data_dir: Path | None = None
    database_url: str | None = None
    frontend_dir: Path | None = None
    encryption_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: float = Field(default=90, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=8)
    llm_validation_retries: int = Field(default=2, ge=0, le=8)

    @field_validator("data_dir", "frontend_dir", mode="before")
    @classmethod
    def empty_path_is_none(cls, value: object) -> object:
        return None if value == "" else value

    def resolved_data_dir(self) -> Path:
        return get_data_directory(str(self.data_dir) if self.data_dir else None)

    def resolved_database_url(self) -> str:
        return self.database_url or default_database_url(self.resolved_data_dir())


settings = Settings()
