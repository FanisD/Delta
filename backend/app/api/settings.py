from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import TypeAdapter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.keyring_store import delete_secret, get_secret, set_secret
from app.core.secrets import EncryptionKeyNotConfigured, encrypt_secret
from app.database import get_session
from app.models.provider import ModelDefaultRecord, ProviderRecord, utc_now
from app.schemas.providers import (
    ModelCapabilitiesResponse,
    ModelDefaultsUpdate,
    ModelRole,
    OllamaModelsResponse,
    ProviderConfigUpdate,
    ProviderConfiguration,
    ProviderId,
    ProviderModelSelection,
    ProviderSettingsResponse,
    ProviderTestRequest,
    ProviderTestResponse,
)
from app.services.llm import LLMClient, LLMError, ProviderCallConfig
from app.services.llm.capabilities import get_model_capabilities
from app.services.llm.settings import load_call_config
from app.services.llm.structured import supported_output_modes

router = APIRouter(tags=["provider settings"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
MODEL_ROLES: tuple[ModelRole, ...] = ("outline", "content", "edit")
KEY_REQUIRED_PROVIDERS: frozenset[ProviderId] = frozenset({"gemini", "anthropic", "xai"})
llm_client = LLMClient()
provider_id_adapter: TypeAdapter[ProviderId] = TypeAdapter(ProviderId)


def to_provider_configuration(record: ProviderRecord) -> ProviderConfiguration:
    key_configured = (
        record.api_key_ciphertext is not None or get_secret(record.provider) is not None
    )
    return ProviderConfiguration(
        provider=provider_id_adapter.validate_python(record.provider),
        configured=(
            record.provider == "ollama" or record.provider == "openai_compatible" or key_configured
        ),
        model=record.model,
        base_url=record.base_url,
        api_key_configured=key_configured,
    )


def provider_test_error(config: ProviderCallConfig, error: LLMError) -> str:
    cause = error.__cause__
    cause_text = str(cause).lower() if cause else ""
    cause_type = type(cause).__name__.lower() if cause else ""
    status_code = getattr(cause, "status_code", None)
    if config.provider == "ollama":
        if "not found" in cause_text and "model" in cause_text:
            return (
                f"Ollama model '{config.model}' is not installed. "
                f"Run `ollama pull {config.model}` and try again."
            )
        if "connect" in cause_text or "connection" in cause_text:
            return f"Unable to connect to Ollama at {config.base_url}. Start Ollama and try again."
    if status_code in (401, 403) or "authentication" in cause_type:
        return "The provider rejected the API key. Check the saved credentials."
    if status_code == 429 or "ratelimit" in cause_type:
        return "The provider rate limit was reached. Wait briefly and retry."
    if "timeout" in cause_type or "timed out" in cause_text:
        return "The provider request timed out. Check connectivity and retry."
    if "not found" in cause_text and "model" in cause_text:
        return f"Model '{config.model}' was not found by this provider."
    if "connect" in cause_text or "connection" in cause_text:
        return "Unable to connect to the provider endpoint. Check its base URL."
    return "The provider request failed. Verify the model name and provider settings."


@router.get(
    "/api/models/capabilities/{provider}",
    response_model=ModelCapabilitiesResponse,
)
async def get_model_capability(
    provider: ProviderId,
    model: Annotated[str, Query(min_length=1, max_length=160)],
) -> ModelCapabilitiesResponse:
    capabilities = get_model_capabilities(provider, model)
    return ModelCapabilitiesResponse(
        provider=provider,
        model=model,
        json_schema=capabilities.json_schema,
        json_mode=capabilities.json_mode,
        tools=capabilities.tools,
        context_window=capabilities.context_window,
        output_modes=list(supported_output_modes(provider, model)),
    )


@router.get("/api/settings/providers", response_model=ProviderSettingsResponse)
async def get_provider_settings(session: SessionDependency) -> ProviderSettingsResponse:
    providers = await session.scalars(select(ProviderRecord).order_by(ProviderRecord.provider))
    defaults = await session.scalars(select(ModelDefaultRecord).order_by(ModelDefaultRecord.role))
    selection_by_role = {
        record.role: ProviderModelSelection(
            provider=provider_id_adapter.validate_python(record.provider), model=record.model
        )
        for record in defaults
    }
    return ProviderSettingsResponse(
        providers=[to_provider_configuration(record) for record in providers],
        defaults={role: selection_by_role.get(role) for role in MODEL_ROLES},
    )


@router.put(
    "/api/settings/providers/{provider}",
    response_model=ProviderConfiguration,
)
async def update_provider_settings(
    provider: ProviderId,
    payload: ProviderConfigUpdate,
    session: SessionDependency,
) -> ProviderConfiguration:
    record = await session.get(ProviderRecord, provider)
    if provider == "openai_compatible" and not payload.base_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="OpenAI-compatible providers require a base URL.",
        )

    key_ciphertext = record.api_key_ciphertext if record else None
    if payload.clear_api_key:
        delete_secret(provider)
        key_ciphertext = None
    elif payload.api_key:
        if set_secret(provider, payload.api_key):
            key_ciphertext = None
        else:
            try:
                key_ciphertext = encrypt_secret(payload.api_key)
            except EncryptionKeyNotConfigured as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=str(exc),
                ) from exc

    if record is None:
        record = ProviderRecord(
            provider=provider,
            model=payload.model,
            api_key_ciphertext=key_ciphertext,
            base_url=payload.base_url,
            updated_at=utc_now(),
        )
        session.add(record)
    else:
        record.model = payload.model
        record.api_key_ciphertext = key_ciphertext
        record.base_url = payload.base_url
        record.updated_at = utc_now()
    if provider in KEY_REQUIRED_PROVIDERS and key_ciphertext is None:
        await session.execute(
            delete(ModelDefaultRecord).where(ModelDefaultRecord.provider == provider)
        )
    await session.commit()
    await session.refresh(record)
    return to_provider_configuration(record)


@router.put("/api/settings/models", response_model=ProviderSettingsResponse)
async def update_model_defaults(
    payload: ModelDefaultsUpdate,
    session: SessionDependency,
) -> ProviderSettingsResponse:
    for role in MODEL_ROLES:
        selection = getattr(payload, role)
        existing = await session.get(ModelDefaultRecord, role)
        if selection is None:
            if existing:
                await session.delete(existing)
            continue
        provider = await session.get(ProviderRecord, selection.provider)
        if provider is None or not to_provider_configuration(provider).configured:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Configure the {selection.provider} provider before assigning it to {role}."
                ),
            )
        if existing is None:
            existing = ModelDefaultRecord(
                role=role,
                provider=selection.provider,
                model=selection.model,
            )
            session.add(existing)
        else:
            existing.provider = selection.provider
            existing.model = selection.model
            existing.updated_at = utc_now()
    await session.commit()
    return await get_provider_settings(session)


@router.post(
    "/api/settings/providers/test",
    response_model=ProviderTestResponse,
)
async def test_provider_connection(
    payload: ProviderTestRequest,
    session: SessionDependency,
) -> ProviderTestResponse:
    try:
        config = await load_call_config(session, payload.provider, model=payload.model)
    except EncryptionKeyNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The {payload.provider} provider has not been configured.",
        )
    if config.provider in KEY_REQUIRED_PROVIDERS and not config.api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Save an API key before testing this cloud provider.",
        )
    try:
        await llm_client.complete(
            [{"role": "user", "content": "Reply with the word OK."}],
            config,
            max_tokens=8,
        )
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=provider_test_error(config, exc),
        ) from exc
    return ProviderTestResponse(ok=True, message="Provider connection succeeded.")


@router.get("/api/providers/ollama/models", response_model=OllamaModelsResponse)
async def list_ollama_models(session: SessionDependency) -> OllamaModelsResponse:
    record = await session.get(ProviderRecord, "ollama")
    base_url = (record.base_url if record else None) or settings.ollama_base_url
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Ollama did not respond within 5 seconds.",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ollama returned HTTP {exc.response.status_code}.",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to connect to Ollama at {base_url}. Start Ollama and try again.",
        ) from exc
    try:
        return OllamaModelsResponse.model_validate(response.json())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ollama returned an invalid model list.",
        ) from exc
