import json

from json_repair import loads as repair_json
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.providers import ProviderId
from app.services.llm.capabilities import get_model_capabilities
from app.services.llm.gateway import LLMClient, LLMError, ProviderCallConfig


class StructuredOutputError(LLMError):
    pass


def _schema_format(model: type[BaseModel], provider: ProviderId) -> dict[str, object]:
    schema = model.model_json_schema()
    if provider == "ollama":
        return schema
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__.lower(),
            "strict": True,
            "schema": schema,
        },
    }


def _unsupported_schema_mode(error: LLMError) -> bool:
    current: BaseException | None = error
    terms = ("response_format", "json_schema", "unsupported", "not support", "format")
    while current is not None:
        text = str(current).lower()
        if any(term in text for term in terms):
            return True
        current = current.__cause__
    return False


def _messages_for_attempt(
    messages: list[dict[str, str]],
    model: type[BaseModel],
    validation_error: str | None,
) -> list[dict[str, str]]:
    instruction = (
        "Return one JSON object matching this schema. Do not include markdown or commentary:\n"
        + json.dumps(model.model_json_schema(), separators=(",", ":"))
    )
    if validation_error:
        instruction += (
            "\nThe previous response failed validation. Correct these issues and return "
            f"the complete object: {validation_error}"
        )
    output = list(messages)
    if output and output[0].get("role") == "system":
        output[0] = {
            "role": "system",
            "content": f"{output[0]['content']}\n\n{instruction}",
        }
    else:
        output.insert(0, {"role": "system", "content": instruction})
    return output


async def generate_structured[ModelT: BaseModel](
    model: type[ModelT],
    messages: list[dict[str, str]],
    config: ProviderCallConfig,
    *,
    client: LLMClient | None = None,
) -> ModelT:
    llm_client = client or LLMClient()
    capabilities = get_model_capabilities(config.provider, config.model)
    modes: list[str] = []
    if capabilities.json_schema:
        modes.append("schema")
    if capabilities.json_mode:
        modes.append("json")
    modes.append("prompt")

    last_validation_error = "The model did not return valid JSON."
    for mode in modes:
        for _ in range(max(1, settings.llm_validation_retries + 1)):
            try:
                result = await llm_client.complete(
                    _messages_for_attempt(
                        messages,
                        model,
                        (
                            last_validation_error
                            if last_validation_error != "The model did not return valid JSON."
                            else None
                        ),
                    ),
                    config,
                    response_format=(
                        _schema_format(model, config.provider)
                        if mode == "schema"
                        else {"type": "json_object"}
                        if mode == "json"
                        else None
                    ),
                )
            except LLMError as exc:
                if mode != "prompt" and _unsupported_schema_mode(exc):
                    break
                raise

            try:
                candidate = repair_json(result.content)
                return model.model_validate(candidate)
            except (ValidationError, ValueError, TypeError) as exc:
                last_validation_error = str(exc)[:2000]

    raise StructuredOutputError(
        f"The model could not produce valid {model.__name__} JSON after retries: "
        f"{last_validation_error}"
    )


def supported_output_modes(provider: ProviderId, model: str) -> tuple[str, ...]:
    capabilities = get_model_capabilities(provider, model)
    modes = []
    if capabilities.json_schema:
        modes.append("native_schema")
    if capabilities.json_mode:
        modes.append("json_mode")
    modes.append("prompt_repair")
    return tuple(modes)
