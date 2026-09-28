from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Reads ../.env (repo root) in local dev; real env vars win in Docker.
    model_config = SettingsConfigDict(env_file="../.env", env_prefix="APP_", extra="ignore")

    app_name: str = "Delta"
    database_url: str = "sqlite+aiosqlite:///../data/app.db"


settings = Settings()
