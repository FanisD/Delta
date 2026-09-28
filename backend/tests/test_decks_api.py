from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.database import Base, get_session
from app.main import app, migrate_database
from app.models.deck import DeckRecord
from app.seed import SEED_DECKS, seed_decks


@pytest.fixture
async def api_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    database_file = tmp_path / "decks-test.sqlite"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_file}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_deck_crud_round_trip(api_client: AsyncClient) -> None:
    payload = {
        "title": "The local-first web",
        "theme": "ocean",
        "cards": [
            {
                "title": "Welcome",
                "layout": "title",
                "blocks": [{"type": "heading", "text": "The local-first web"}],
            }
        ],
    }

    created = await api_client.post("/api/decks", json=payload)
    assert created.status_code == 201
    deck = created.json()
    deck_id = deck["id"]
    assert deck["cards"][0]["blocks"][0]["type"] == "heading"

    listed = await api_client.get("/api/decks")
    assert [item["id"] for item in listed.json()] == [deck_id]

    updated = await api_client.patch(
        f"/api/decks/{deck_id}", json={"title": "A renamed presentation"}
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "A renamed presentation"
    assert updated.json()["cards"] == deck["cards"]

    deleted = await api_client.delete(f"/api/decks/{deck_id}")
    assert deleted.status_code == 204
    assert (await api_client.get(f"/api/decks/{deck_id}")).status_code == 404


@pytest.mark.asyncio
async def test_create_rejects_invalid_document(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/decks",
        json={
            "title": "Invalid presentation",
            "theme": "ultraviolet",
            "cards": [],
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shared_layout_catalog_has_eight_layouts(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/layouts")

    assert response.status_code == 200
    assert {layout["id"] for layout in response.json()} == {
        "title",
        "single_column",
        "two_column",
        "three_column",
        "image_left",
        "image_right",
        "quote",
        "timeline",
    }


@pytest.mark.asyncio
async def test_seed_decks_are_valid_and_idempotent(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'seed-test.sqlite'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        await seed_decks(session)
        await seed_decks(session)
        records = await session.scalars(select(DeckRecord))
        decks = list(records)

    assert len(decks) == len(SEED_DECKS)
    assert {deck.id for deck in decks} == {seed["id"] for seed in SEED_DECKS}
    await engine.dispose()


def test_concurrent_database_startup_migrates_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_file = tmp_path / "concurrent-startup.sqlite"
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{database_file}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        migrations = [executor.submit(migrate_database) for _ in range(2)]
        for migration in migrations:
            migration.result()

    with create_engine(f"sqlite:///{database_file}").connect() as connection:
        revision: str = connection.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
        tables: list[str] = inspect(connection).get_table_names()
    assert revision == "0002_llm_provider_settings"
    assert {"decks", "llm_providers", "llm_model_defaults"}.issubset(tables)
