from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.secrets import decrypt_secret
from app.models.provider import ProviderRecord
from app.schemas.providers import ProviderId
from app.services.llm.gateway import ProviderCallConfig

provider_id_adapter: TypeAdapter[ProviderId] = TypeAdapter(ProviderId)


def to_call_config(record: ProviderRecord) -> ProviderCallConfig:
    return ProviderCallConfig(
        provider=provider_id_adapter.validate_python(record.provider),
        model=record.model,
        api_key=(decrypt_secret(record.api_key_ciphertext) if record.api_key_ciphertext else None),
        base_url=record.base_url
        or (settings.ollama_base_url if record.provider == "ollama" else None),
    )


async def load_call_config(
    session: AsyncSession,
    provider: ProviderId,
    *,
    model: str | None = None,
) -> ProviderCallConfig | None:
    record = await session.get(ProviderRecord, provider)
    if record is None:
        return None
    config = to_call_config(record)
    if model:
        return ProviderCallConfig(
            provider=config.provider,
            model=model,
            api_key=config.api_key,
            base_url=config.base_url,
        )
    return config
