import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI
from filelock import FileLock
from pydantic import BaseModel

from alembic import command
from app.api.decks import router as decks_router
from app.core.config import settings
from app.database import session_factory
from app.layouts import load_layouts
from app.seed import seed_decks


def migrate_database() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    data_directory = backend_root.parent / "data"
    data_directory.mkdir(parents=True, exist_ok=True)
    with FileLock(str(data_directory / ".migration.lock"), timeout=120):
        alembic_config = Config(str(backend_root / "alembic.ini"))
        alembic_config.set_main_option("script_location", str(backend_root / "alembic"))
        command.upgrade(alembic_config, "head")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await asyncio.to_thread(migrate_database)
    async with session_factory() as session:
        await seed_decks(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(decks_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/health")
@app.get("/api/health", include_in_schema=False)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/api/layouts", tags=["layouts"])
def get_layouts() -> list[dict[str, object]]:
    return load_layouts()
