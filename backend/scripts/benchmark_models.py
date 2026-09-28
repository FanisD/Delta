import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from time import perf_counter

from sqlalchemy import select

from app.database import engine, session_factory
from app.models.provider import ProviderRecord
from app.services.llm import LLMClient, LLMError
from app.services.llm.settings import to_call_config

PROMPTS = (
    "Return JSON with a title and a numeric count for three local-first benefits.",
    "Return JSON with a title and a numeric count for four helpful presentation tips.",
    "Return JSON with a title and a numeric count for two ways to show data clearly.",
)


@dataclass
class ModelBenchmark:
    provider: str
    model: str
    calls: int
    valid_json: int
    valid_json_rate: float
    average_latency_seconds: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float | None
    error: str | None = None


async def benchmark_provider(record: ProviderRecord, client: LLMClient) -> ModelBenchmark:
    config = to_call_config(record)
    latencies: list[float] = []
    prompt_tokens = 0
    completion_tokens = 0
    valid_json = 0
    cost_estimates: list[float] = []
    errors: list[str] = []

    for prompt in PROMPTS:
        started = perf_counter()
        try:
            result = await client.complete(
                [{"role": "user", "content": prompt}],
                config,
                max_tokens=128,
                response_format={"type": "json_object"},
            )
            latencies.append(perf_counter() - started)
            prompt_tokens += result.prompt_tokens or 0
            completion_tokens += result.completion_tokens or 0
            if result.estimated_cost_usd is not None:
                cost_estimates.append(result.estimated_cost_usd)
            try:
                json.loads(result.content)
                valid_json += 1
            except json.JSONDecodeError:
                continue
        except LLMError as exc:
            latencies.append(perf_counter() - started)
            errors.append(str(exc))

    calls = len(PROMPTS)
    return ModelBenchmark(
        provider=record.provider,
        model=record.model,
        calls=calls,
        valid_json=valid_json,
        valid_json_rate=valid_json / calls,
        average_latency_seconds=sum(latencies) / len(latencies) if latencies else 0,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost_usd=sum(cost_estimates) if len(cost_estimates) == calls else None,
        error="; ".join(dict.fromkeys(errors)) if errors else None,
    )


async def run_benchmarks() -> list[ModelBenchmark]:
    try:
        async with session_factory() as session:
            records = list(
                await session.scalars(select(ProviderRecord).order_by(ProviderRecord.provider))
            )
        if not records:
            return []
        client = LLMClient()
        results = []
        for record in records:
            try:
                results.append(await benchmark_provider(record, client))
            except Exception as exc:
                results.append(
                    ModelBenchmark(
                        provider=record.provider,
                        model=record.model,
                        calls=len(PROMPTS),
                        valid_json=0,
                        valid_json_rate=0,
                        average_latency_seconds=0,
                        prompt_tokens=0,
                        completion_tokens=0,
                        estimated_cost_usd=None,
                        error=(
                            f"Unable to benchmark saved provider settings ({type(exc).__name__})."
                        ),
                    )
                )
        return results
    finally:
        await engine.dispose()


def main() -> int:
    try:
        results = asyncio.run(run_benchmarks())
    except Exception as exc:
        print(
            f"Benchmark could not read provider settings ({type(exc).__name__}). "
            "Start Delta once so its database migrations have run.",
            file=sys.stderr,
        )
        return 1
    if not results:
        print("No provider models are configured. Save provider settings first.", file=sys.stderr)
        return 1
    print(json.dumps([asdict(result) for result in results], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
