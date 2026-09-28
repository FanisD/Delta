import asyncio
from collections import deque
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.providers import ProviderId
from app.services.llm.capabilities import get_model_capabilities
from app.services.llm.gateway import LLMClient, LLMError, LLMResult, ProviderCallConfig
from app.services.llm.structured import generate_structured, supported_output_modes


class SampleResponse(BaseModel):
    title: str
    count: int


class StubLLMClient(LLMClient):
    def __init__(self, contents: list[str | Exception]) -> None:
        self.contents = deque(contents)
        self.calls: list[dict[str, object]] = []

    async def complete(
        self,
        messages: list[dict[str, str]],
        config: ProviderCallConfig,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_format: dict[str, object] | None = None,
        timeout: float | None = None,
    ) -> LLMResult:
        self.calls.append({"messages": messages, "response_format": response_format})
        result = self.contents.popleft()
        if isinstance(result, Exception):
            raise result
        return LLMResult(result, 2, 3, 5, None, False)


@pytest.mark.asyncio
async def test_structured_output_validates_and_repairs_json() -> None:
    client = StubLLMClient(['```json\n{"title":"A repaired title","count":2,}\n```'])
    config = ProviderCallConfig("gemini", "gemini-2.5-flash", api_key="not-used")

    result = await generate_structured(
        SampleResponse,
        [{"role": "user", "content": "Make an example."}],
        config,
        client=client,
    )

    assert result == SampleResponse(title="A repaired title", count=2)
    response_format = client.calls[0]["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    messages = client.calls[0]["messages"]
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"


@pytest.mark.asyncio
async def test_structured_output_retries_validation_with_error_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_validation_retries", 1)
    client = StubLLMClient(
        ['{"title":"Wrong type","count":"many"}', '{"title":"Corrected","count":3}']
    )
    config = ProviderCallConfig("ollama", "qwen2.5:7b")

    result = await generate_structured(
        SampleResponse,
        [{"role": "user", "content": "Make an example."}],
        config,
        client=client,
    )

    assert result.count == 3
    messages = client.calls[1]["messages"]
    assert isinstance(messages, list)
    second_system_message = messages[0]["content"]
    assert "previous response failed validation" in second_system_message.lower()
    assert isinstance(client.calls[0]["response_format"], dict)
    response_format = client.calls[0]["response_format"]
    assert isinstance(response_format, dict)
    assert response_format.get("properties") is not None


@pytest.mark.asyncio
async def test_structured_output_falls_back_when_provider_rejects_schema() -> None:
    unsupported = LLMError("provider rejected response_format json_schema")
    client = StubLLMClient([unsupported, '{"title":"Fallback","count":1}'])
    config = ProviderCallConfig("gemini", "gemini-2.5-flash")
    unsupported.__cause__ = RuntimeError("response_format is not supported")

    result = await generate_structured(
        SampleResponse,
        [{"role": "user", "content": "Make an example."}],
        config,
        client=client,
    )

    assert result.title == "Fallback"
    assert client.calls[1]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_gateway_retries_transient_errors_and_uses_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    captured: list[dict[str, object]] = []

    async def fake_completion(**kwargs: object) -> SimpleNamespace:
        nonlocal attempts
        attempts += 1
        captured.append(kwargs)
        if attempts == 1:
            raise TimeoutError("temporary timeout")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Ready"))],
            usage=None,
        )

    async def no_wait(_: float) -> None:
        return None

    monkeypatch.setattr("app.services.llm.gateway.litellm.acompletion", fake_completion)
    monkeypatch.setattr(asyncio, "sleep", no_wait)
    monkeypatch.setattr(settings, "llm_max_retries", 1)
    result = await LLMClient().complete(
        [{"role": "user", "content": "Say ready"}],
        ProviderCallConfig("anthropic", "claude-3-7-sonnet", api_key="key"),
    )

    assert attempts == 2
    assert captured[0]["model"] == "anthropic/claude-3-7-sonnet"
    assert result.content == "Ready"
    assert result.usage_is_estimated is True
    assert result.total_tokens is not None
    assert result.prompt_tokens is not None
    assert result.completion_tokens is not None
    assert result.total_tokens == result.prompt_tokens + result.completion_tokens


@pytest.mark.asyncio
async def test_gateway_streams_text_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_stream(**_: object) -> AsyncIterator[SimpleNamespace]:
        for value in ("first", " second"):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=value))])

    async def fake_completion(**_: object) -> AsyncIterator[SimpleNamespace]:
        return fake_stream()

    monkeypatch.setattr("app.services.llm.gateway.litellm.acompletion", fake_completion)
    chunks = [
        chunk
        async for chunk in LLMClient().stream(
            [{"role": "user", "content": "Stream"}],
            ProviderCallConfig("ollama", "llama3.2"),
        )
    ]

    assert "".join(chunks) == "first second"


@pytest.mark.parametrize(
    ("provider", "model", "prefix"),
    [
        ("gemini", "gemini-2.5-flash", "gemini/"),
        ("anthropic", "claude-3-7-sonnet", "anthropic/"),
        ("xai", "grok-3-mini", "xai/"),
        ("openai_compatible", "my-model", "openai/"),
        ("ollama", "qwen2.5:7b", "ollama_chat/"),
    ],
)
def test_provider_model_prefixes(provider: ProviderId, model: str, prefix: str) -> None:
    assert ProviderCallConfig(provider, model).litellm_model == f"{prefix}{model}"


def test_model_capability_registry_has_fallback_ladder() -> None:
    assert get_model_capabilities("gemini", "gemini-2.5-flash").context_window == 1_048_576
    assert supported_output_modes("ollama", "qwen2.5:7b") == (
        "native_schema",
        "json_mode",
        "prompt_repair",
    )
    assert supported_output_modes("openai_compatible", "local-model") == (
        "json_mode",
        "prompt_repair",
    )
