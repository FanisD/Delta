from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import respx
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.settings import llm_client
from app.core.config import settings
from app.database import Base, get_session
from app.main import app
from app.models.provider import ProviderRecord
from app.services.llm.gateway import LLMError, LLMResult, ProviderCallConfig


@pytest.fixture
async def settings_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'settings-test.sqlite'}")
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
async def test_provider_key_is_encrypted_and_never_returned(
    settings_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "encryption_key", Fernet.generate_key().decode())
    secret = "sk-test-provider-key"
    response = await settings_client.put(
        "/api/settings/providers/gemini",
        json={"model": "gemini-2.5-flash", "api_key": secret},
    )

    assert response.status_code == 200
    assert response.json()["api_key_configured"] is True
    assert secret not in response.text

    session_generator = app.dependency_overrides[get_session]()
    session = await anext(session_generator)
    try:
        record = await session.get(ProviderRecord, "gemini")
        assert record is not None
        assert record.api_key_ciphertext != secret
        assert secret not in record.api_key_ciphertext
    finally:
        await session_generator.aclose()

    fetched = await settings_client.get("/api/settings/providers")
    assert secret not in fetched.text
    assert fetched.json()["providers"][0]["configured"] is True


@pytest.mark.asyncio
async def test_provider_key_requires_encryption_key(
    settings_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "encryption_key", None)
    response = await settings_client.put(
        "/api/settings/providers/anthropic",
        json={"model": "claude-3-7-sonnet", "api_key": "secret"},
    )

    assert response.status_code == 503
    assert "APP_ENCRYPTION_KEY" in response.json()["detail"]


@pytest.mark.asyncio
async def test_model_defaults_and_provider_test(
    settings_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "encryption_key", Fernet.generate_key().decode())
    await settings_client.put(
        "/api/settings/providers/gemini",
        json={"model": "gemini-2.5-flash", "api_key": "encrypted-test-key"},
    )
    response = await settings_client.put(
        "/api/settings/models",
        json={
            "outline": {"provider": "gemini", "model": "gemini-2.5-flash"},
            "content": {"provider": "gemini", "model": "gemini-2.5-pro"},
            "edit": None,
        },
    )
    assert response.status_code == 200
    assert response.json()["defaults"]["content"]["model"] == "gemini-2.5-pro"

    async def fake_complete(
        messages: list[dict[str, str]], config: object, **kwargs: object
    ) -> LLMResult:
        assert isinstance(config, ProviderCallConfig)
        assert config.api_key == "encrypted-test-key"
        return LLMResult("OK", 2, 1, 3, None, False)

    monkeypatch.setattr(llm_client, "complete", fake_complete)
    test_result = await settings_client.post(
        "/api/settings/providers/test", json={"provider": "gemini"}
    )
    assert test_result.status_code == 200
    assert test_result.json()["ok"] is True
    assert "encrypted-test-key" not in test_result.text


@pytest.mark.asyncio
async def test_ollama_model_discovery_reports_server_unavailable(
    settings_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama.local")
    with respx.mock(assert_all_called=True) as router:
        router.get("http://ollama.local/api/tags").mock(
            return_value=Response(200, json={"models": []})
        )
        response = await settings_client.get("/api/providers/ollama/models")

    assert response.status_code == 200
    assert response.json() == {"models": []}


@pytest.mark.asyncio
async def test_ollama_model_discovery_explains_server_unavailable(
    settings_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "ollama_base_url", "http://ollama.local")
    with respx.mock(assert_all_called=True) as router:
        router.get("http://ollama.local/api/tags").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        response = await settings_client.get("/api/providers/ollama/models")

    assert response.status_code == 502
    assert "Start Ollama" in response.json()["detail"]


@pytest.mark.asyncio
async def test_capability_api_exposes_structured_output_fallbacks(
    settings_client: AsyncClient,
) -> None:
    response = await settings_client.get(
        "/api/models/capabilities/ollama", params={"model": "qwen2.5:7b"}
    )

    assert response.status_code == 200
    assert response.json()["output_modes"] == [
        "native_schema",
        "json_mode",
        "prompt_repair",
    ]


@pytest.mark.asyncio
async def test_ollama_test_connection_explains_missing_model(
    settings_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    await settings_client.put("/api/settings/providers/ollama", json={"model": "qwen2.5:7b"})

    async def missing_model(
        messages: list[dict[str, str]], config: object, **kwargs: object
    ) -> LLMResult:
        error = LLMError("Provider request failed")
        error.__cause__ = RuntimeError("model 'qwen2.5:7b' not found")
        raise error

    monkeypatch.setattr(llm_client, "complete", missing_model)
    response = await settings_client.post(
        "/api/settings/providers/test", json={"provider": "ollama"}
    )

    assert response.status_code == 502
    assert "ollama pull qwen2.5:7b" in response.json()["detail"]


@pytest.mark.asyncio
async def test_defaults_reject_unconfigured_provider(settings_client: AsyncClient) -> None:
    response = await settings_client.put(
        "/api/settings/models",
        json={
            "outline": {"provider": "gemini", "model": "gemini-2.5-flash"},
            "content": None,
            "edit": None,
        },
    )

    assert response.status_code == 422
    assert "Configure the gemini provider" in response.json()["detail"]
