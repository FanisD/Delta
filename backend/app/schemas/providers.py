from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProviderId = Literal["gemini", "anthropic", "xai", "openai_compatible", "ollama"]
ModelRole = Literal["outline", "content", "edit"]


class ProviderConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1, max_length=160)
    api_key: str | None = Field(default=None, min_length=1, max_length=4096)
    clear_api_key: bool = False
    base_url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def key_update_must_be_unambiguous(self) -> "ProviderConfigUpdate":
        if self.api_key is not None and self.clear_api_key:
            raise ValueError("Provide a new API key or clear the saved key, not both")
        return self

    @field_validator("model")
    @classmethod
    def model_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Model must not be blank")
        return normalized

    @field_validator("api_key")
    @classmethod
    def api_key_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("API key must not be blank")
        return value

    @field_validator("base_url")
    @classmethod
    def base_url_must_be_http_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Base URL must be a valid HTTP or HTTPS URL.")
        return normalized.rstrip("/")


class ProviderConfiguration(BaseModel):
    provider: ProviderId
    configured: bool
    model: str | None
    base_url: str | None
    api_key_configured: bool


class ProviderModelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderId
    model: str = Field(min_length=1, max_length=160)

    @field_validator("model")
    @classmethod
    def model_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Model must not be blank")
        return normalized


class ModelDefaultsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outline: ProviderModelSelection | None
    content: ProviderModelSelection | None
    edit: ProviderModelSelection | None


class ProviderSettingsResponse(BaseModel):
    providers: list[ProviderConfiguration]
    defaults: dict[ModelRole, ProviderModelSelection | None]


class ProviderTestRequest(BaseModel):
    provider: ProviderId
    model: str | None = Field(default=None, min_length=1, max_length=160)


class ProviderTestResponse(BaseModel):
    ok: bool
    message: str


class OllamaModel(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class OllamaModelsResponse(BaseModel):
    models: list[OllamaModel]


class ModelCapabilitiesResponse(BaseModel):
    provider: ProviderId
    model: str
    json_schema: bool
    json_mode: bool
    tools: bool
    context_window: int | None
    output_modes: list[str]
