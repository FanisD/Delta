"""Small-context map/reduce helpers used by imports and generation."""

from collections.abc import Awaitable, Callable

ChunkFn = Callable[[str], Awaitable[str]]


def split_text(text: str, max_chars: int = 6000) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    return [normalized[start : start + max_chars] for start in range(0, len(normalized), max_chars)]


async def map_reduce_text(text: str, mapper: ChunkFn, reducer: ChunkFn | None = None) -> str:
    """Summarize chunks independently, then optionally combine their summaries."""
    chunks = split_text(text)
    if len(chunks) <= 1:
        return text.strip()
    summaries = [await mapper(chunk) for chunk in chunks]
    combined = "\n".join(summary.strip() for summary in summaries if summary.strip())
    return await reducer(combined) if reducer and combined else combined
