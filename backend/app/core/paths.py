from pathlib import Path

from platformdirs import user_data_dir

APP_DATA_ENV = "APP_DATA_DIR"


def get_data_directory(configured_directory: str | None = None) -> Path:
    """Return the durable application-data directory.

    ``APP_DATA_DIR`` is intentionally supported for development and tests so
    they never write into a user's real profile.
    """

    directory = configured_directory or user_data_dir("Delta", "FanisD")
    path = Path(directory).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_database_url(data_directory: Path) -> str:
    return f"sqlite+aiosqlite:///{(data_directory / 'delta.db').as_posix()}"


def assets_directory(configured_directory: str | None = None) -> Path:
    path = get_data_directory(configured_directory) / "assets"
    path.mkdir(parents=True, exist_ok=True)
    return path
