from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_session
from app.main import app
from app.schemas.generation import GenerationSettings, OutlineItem
from app.services.generation import create_card, create_outline


@pytest.fixture
async def generation_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'generation.sqlite'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_outline_endpoint_returns_editable_items(generation_client: AsyncClient) -> None:
    response = await generation_client.post(
        "/api/generation/outline",
        json={
            "prompt": "How local-first software protects user data",
            "settings": {"card_count": 3, "tone": "warm"},
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result["items"]) == 3
    assert all(item["id"] and item["title"] and item["summary"] for item in result["items"])


@pytest.mark.asyncio
async def test_card_generation_uses_safe_deterministic_layout() -> None:
    settings = GenerationSettings()
    outline = await create_outline("A metrics story", settings)
    item = OutlineItem(id="card-1", title="Metrics and data", summary="Compare the key numbers.")
    card = await create_card(outline, item, settings)
    assert card.id == "card-1"
    assert card.layout.value == "two_column"
    assert card.blocks
