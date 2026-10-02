import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, cast

from alembic.config import Config
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from filelock import FileLock
from pydantic import BaseModel

from alembic import command
from app.api.ai import router as ai_router
from app.api.assets import router as assets_router
from app.api.decks import router as decks_router
from app.api.exports import router as exports_router
from app.api.generation import router as generation_router
from app.api.imports import router as imports_router
from app.api.settings import router as settings_router
from app.core.config import settings
from app.database import engine, session_factory
from app.layouts import load_layouts
from app.models.image import ImageJobRecord
from app.seed import seed_decks


def migrate_database() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    data_directory = settings.resolved_data_dir()
    with FileLock(str(data_directory / ".migration.lock"), timeout=120):
        alembic_config = Config(str(backend_root / "alembic.ini"))
        alembic_config.set_main_option("script_location", str(backend_root / "alembic"))
        alembic_config.set_main_option("sqlalchemy.url", settings.resolved_database_url())
        command.upgrade(alembic_config, "head")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await asyncio.to_thread(migrate_database)
    async with engine.begin() as connection:
        image_table = cast(Any, ImageJobRecord.__table__)
        await connection.run_sync(image_table.create, checkfirst=True)
    async with session_factory() as session:
        await seed_decks(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(decks_router)
app.include_router(settings_router)
app.include_router(generation_router)
app.include_router(ai_router)
app.include_router(assets_router)
app.include_router(exports_router)
app.include_router(imports_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/health")
@app.get("/api/health", include_in_schema=False)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/layouts", tags=["layouts"])
def get_layouts() -> list[dict[str, object]]:
    return load_layouts()


def _frontend_directory() -> Path:
    if settings.frontend_dir:
        return settings.frontend_dir
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


frontend_directory = _frontend_directory()
if frontend_directory.is_dir():

    @app.get("/print/{deck_id}", include_in_schema=False)
    def print_route(_: str) -> FileResponse:
        return FileResponse(frontend_directory / "index.html")

    app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
