import pytest
from pydantic import ValidationError

from app.schemas.providers import (
    ModelDefaultsUpdate,
    ProviderConfigUpdate,
    ProviderModelSelection,
)


def test_provider_configuration_accepts_supported_providers() -> None:
    assert ProviderConfigUpdate(model="gemini-2.5-flash", api_key="secret").model == (
        "gemini-2.5-flash"
    )


def test_provider_configuration_rejects_blank_model_and_key() -> None:
    with pytest.raises(ValidationError):
        ProviderConfigUpdate(model=" ")
    with pytest.raises(ValidationError):
        ProviderConfigUpdate(model="gemini-2.5-flash", api_key=" ")


def test_model_defaults_require_provider_and_model_together() -> None:
    with pytest.raises(ValidationError):
        ProviderModelSelection(provider="gemini", model=" ")

    defaults = ModelDefaultsUpdate(
        outline=ProviderModelSelection(provider="gemini", model="gemini-2.5-flash"),
        content=None,
        edit=None,
    )
    assert defaults.outline is not None
    assert defaults.outline.provider == "gemini"
