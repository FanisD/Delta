from collections import deque

import pytest

from app.models.provider import ProviderRecord
from app.services.llm.gateway import LLMClient, LLMResult, ProviderCallConfig
from scripts.benchmark_models import benchmark_provider


class BenchmarkClient(LLMClient):
    def __init__(self) -> None:
        self.responses = deque(
            [
                LLMResult('{"title":"Good","count":3}', 10, 8, 18, 0.01, False),
                LLMResult("not JSON", 10, 4, 14, 0.02, False),
                LLMResult('{"title":"Also good","count":2}', 10, 8, 18, 0.03, False),
            ]
        )

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
        assert response_format == {"type": "json_object"}
        return self.responses.popleft()


@pytest.mark.asyncio
async def test_benchmark_reports_valid_json_latency_tokens_and_cost() -> None:
    result = await benchmark_provider(
        ProviderRecord(provider="gemini", model="gemini-2.5-flash"),
        BenchmarkClient(),
    )

    assert result.calls == 3
    assert result.valid_json == 2
    assert result.valid_json_rate == pytest.approx(2 / 3)
    assert result.average_latency_seconds >= 0
    assert result.prompt_tokens == 30
    assert result.completion_tokens == 20
    assert result.estimated_cost_usd == pytest.approx(0.06)
