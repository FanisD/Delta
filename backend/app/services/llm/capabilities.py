from dataclasses import dataclass

from app.schemas.providers import ProviderId


@dataclass(frozen=True)
class ModelCapabilities:
    json_schema: bool
    json_mode: bool
    tools: bool
    context_window: int | None


_PROVIDER_DEFAULTS: dict[ProviderId, ModelCapabilities] = {
    "gemini": ModelCapabilities(True, True, True, None),
    "anthropic": ModelCapabilities(True, True, True, None),
    "xai": ModelCapabilities(True, True, True, None),
    "openai_compatible": ModelCapabilities(False, True, False, None),
    "ollama": ModelCapabilities(True, True, False, None),
}


def get_model_capabilities(provider: ProviderId, model: str) -> ModelCapabilities:
    capabilities = _PROVIDER_DEFAULTS[provider]
    normalized = model.lower()
    context_window = capabilities.context_window
    if "gemini-2.5" in normalized:
        context_window = 1_048_576
    elif "claude" in normalized:
        context_window = 200_000
    elif "grok" in normalized:
        context_window = 131_072
    elif "gpt-4o" in normalized:
        context_window = 128_000
    return ModelCapabilities(
        json_schema=capabilities.json_schema,
        json_mode=capabilities.json_mode,
        tools=capabilities.tools,
        context_window=context_window,
    )
