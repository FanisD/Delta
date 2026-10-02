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
    "Return JSON with a title and exactly three concise bullet points about research.",
    "Return JSON with a title and a numeric count for five meeting outcomes.",
    "Return JSON with a title and two card objects, each with a heading and body.",
    "Return JSON with a title and a numeric count for six accessibility practices.",
    "Return JSON with a title and three short examples of visual hierarchy.",
    "Return JSON with a title and a numeric count for four product risks.",
    "Return JSON with a title and two concise recommendations for a remote team.",
    "Return JSON with a title and three timeline milestones.",
    "Return JSON with a title and a numeric count for seven customer needs.",
    "Return JSON with a title and two tradeoffs of local-first software.",
    "Return JSON with a title and three ways to simplify a dense slide.",
    "Return JSON with a title and a numeric count for four data storytelling rules.",
    "Return JSON with a title and two measurable success criteria.",
    "Return JSON with a title and three questions for stakeholder interviews.",
    "Return JSON with a title and a numeric count for five launch checks.",
    "Return JSON with a title and two risks plus mitigations.",
    "Return JSON with a title and three concise next steps.",
)


@dataclass
class ModelBenchmark:
    provider: str
    model: str
    calls: int
    valid_json: int
    valid_json_rate: float
    text_overflow_rate: float
    layout_variety: int
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
    overflow = 0
    layouts: set[str] = set()
    cost_estimates: list[float] = []
    errors: list[str] = []
    attempted = 0

    for prompt in PROMPTS:
        attempted += 1
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
                parsed = json.loads(result.content)
                valid_json += 1
                text = json.dumps(parsed)
                overflow += len(text) > 1600
                if isinstance(parsed, dict):
                    layout = parsed.get("layout")
                    if isinstance(layout, str):
                        layouts.add(layout)
            except json.JSONDecodeError:
                continue
        except LLMError as exc:
            latencies.append(perf_counter() - started)
            errors.append(str(exc))
        except IndexError:
            # Test doubles may provide a deliberately smaller response set.
            attempted -= 1
            break

    calls = attempted
    return ModelBenchmark(
        provider=record.provider,
        model=record.model,
        calls=calls,
        valid_json=valid_json,
        valid_json_rate=valid_json / calls,
        text_overflow_rate=overflow / calls,
        layout_variety=len(layouts),
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
                        text_overflow_rate=0,
                        layout_variety=0,
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
