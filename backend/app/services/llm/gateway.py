import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from math import ceil
from typing import Any

import litellm

from app.core.config import settings
from app.schemas.providers import ProviderId

litellm.suppress_debug_info = True


@dataclass(frozen=True)
class ProviderCallConfig:
    provider: ProviderId
    model: str
    api_key: str | None = None
    base_url: str | None = None

    @property
    def litellm_model(self) -> str:
        prefix = {
            "gemini": "gemini/",
            "anthropic": "anthropic/",
            "xai": "xai/",
            "openai_compatible": "openai/",
            "ollama": "ollama_chat/",
        }[self.provider]
        if prefix and self.model.startswith(prefix):
            return self.model
        return f"{prefix}{self.model}"


@dataclass(frozen=True)
class LLMResult:
    content: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float | None
    usage_is_estimated: bool
    tool_calls: Any = None


class LLMError(RuntimeError):
    pass


def _is_retryable(error: Exception) -> bool:
    retryable_names = {
        "APIConnectionError",
        "InternalServerError",
        "RateLimitError",
        "ServiceUnavailableError",
        "Timeout",
        "TimeoutError",
    }
    return type(error).__name__ in retryable_names


def _request_arguments(
    config: ProviderCallConfig,
    *,
    temperature: float,
    max_tokens: int,
    timeout: float,
    stream: bool,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        "model": config.litellm_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout,
        "num_retries": 0,
        "stream": stream,
    }
    if config.api_key:
        arguments["api_key"] = config.api_key
    if config.base_url:
        arguments["api_base"] = config.base_url
    return arguments


def _estimate_tokens(text: str) -> int:
    return max(1, ceil(len(text) / 4))


def _cost_estimate(
    config: ProviderCallConfig, prompt_tokens: int, completion_tokens: int
) -> float | None:
    model_info = litellm.model_cost.get(config.litellm_model)
    if model_info is None:
        return None
    input_cost = model_info.get("input_cost_per_token")
    output_cost = model_info.get("output_cost_per_token")
    if not isinstance(input_cost, (int, float)) or not isinstance(output_cost, (int, float)):
        return None
    return float(prompt_tokens * input_cost + completion_tokens * output_cost)


class LLMClient:
    async def complete(
        self,
        messages: list[dict[str, str]],
        config: ProviderCallConfig,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        response_format: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> LLMResult:
        limit = timeout or settings.llm_timeout_seconds
        arguments = _request_arguments(
            config,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=limit,
            stream=False,
        )
        arguments["messages"] = messages
        if response_format:
            if config.provider == "ollama":
                arguments["format"] = (
                    "json" if response_format == {"type": "json_object"} else response_format
                )
            else:
                arguments["response_format"] = response_format

        response = await self._with_retry(arguments, limit)
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMError("The model returned an empty or invalid completion.") from exc
        tool_calls = getattr(response.choices[0].message, "tool_calls", None)
        if not isinstance(content, str):
            if tool_calls:
                content = ""
            else:
                raise LLMError("The model returned a non-text completion.")
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        usage_is_estimated = prompt_tokens is None or completion_tokens is None
        prompt_tokens = prompt_tokens or _estimate_tokens(
            "\n".join(message["content"] for message in messages)
        )
        completion_tokens = completion_tokens or _estimate_tokens(content)
        total_tokens = total_tokens or prompt_tokens + completion_tokens
        return LLMResult(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=_cost_estimate(config, prompt_tokens, completion_tokens),
            usage_is_estimated=usage_is_estimated,
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list[dict[str, str]],
        config: ProviderCallConfig,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        timeout: float | None = None,
    ) -> AsyncIterator[str]:
        limit = timeout or settings.llm_timeout_seconds
        arguments = _request_arguments(
            config,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=limit,
            stream=True,
        )
        arguments["messages"] = messages
        stream = await self._with_retry(arguments, limit)
        try:
            async with asyncio.timeout(limit):
                async for chunk in stream:
                    choices = getattr(chunk, "choices", [])
                    if choices:
                        text = getattr(getattr(choices[0], "delta", None), "content", None)
                        if isinstance(text, str):
                            yield text
        except TimeoutError as exc:
            raise LLMError("The model response timed out while streaming.") from exc
        except Exception as exc:
            raise LLMError("The model stream failed.") from exc

    async def _with_retry(self, arguments: dict[str, Any], timeout: float) -> Any:
        attempts = max(1, settings.llm_max_retries + 1)
        for attempt in range(attempts):
            try:
                async with asyncio.timeout(timeout):
                    return await litellm.acompletion(**arguments)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not _is_retryable(exc) or attempt == attempts - 1:
                    raise LLMError(
                        "The model request failed. Check provider settings and connectivity."
                    ) from exc
                await asyncio.sleep(0.5 * (2**attempt))
        raise LLMError("The model request failed.")
