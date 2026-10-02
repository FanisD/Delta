from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.deck import Card, Layout
from app.schemas.generation import GenerationSettings, Outline, OutlineItem
from app.services.llm.settings import load_call_config
from app.services.llm.structured import generate_structured

_PROMPTS = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parents[1] / "prompts"),
    undefined=StrictUndefined,
    autoescape=False,
)

THEME_STYLE_HINTS = {
    "ocean": "clean editorial photography, cool blue palette, soft natural light",
    "sunset": "warm cinematic photography, coral and amber palette, long shadows",
    "forest": "calm modern photography, deep green palette, organic textures",
}


def image_prompt(card: Card, theme: str = "ocean") -> str:
    """Create a provider-neutral prompt without making an LLM call."""
    text = " ".join(
        block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "")
        for block in card.model_dump(mode="python")["blocks"]
    )
    hint = THEME_STYLE_HINTS.get(theme, THEME_STYLE_HINTS["ocean"])
    return f"{card.title}: {text[:700]}. {hint}. No text, logos, or watermarks."


def _fallback_outline(prompt: str, settings: GenerationSettings) -> Outline:
    topic = " ".join(prompt.split()).strip().rstrip(".") or "Your presentation"
    names = ["The big idea", "Why it matters", "Key insights", "Practical approach", "Next steps"]
    items = [
        OutlineItem(
            id=str(uuid4()),
            title=(topic[:100] if index == 0 else f"{name}: {topic[:70]}"),
            summary=f"A {settings.density} overview of {topic.lower()}.",
        )
        for index, name in enumerate(names[: settings.card_count])
    ]
    while len(items) < settings.card_count:
        items.append(
            OutlineItem(
                id=str(uuid4()),
                title=f"More to explore: {topic[:70]}",
                summary=f"Additional context and examples about {topic.lower()}.",
            )
        )
    return Outline(title=topic[:240], items=items)


async def create_outline(
    prompt: str, settings: GenerationSettings, session: AsyncSession | None = None
) -> Outline:
    if session is not None:
        config = await load_call_config(session, "ollama")
        if config:
            rendered = _PROMPTS.get_template("outline.jinja2").render(
                prompt=prompt, settings=settings
            )
            try:
                return await generate_structured(
                    Outline,
                    [{"role": "user", "content": rendered}],
                    config,
                )
            except Exception:
                pass
    return _fallback_outline(prompt, settings)


def _fallback_layout(item: OutlineItem) -> Layout:
    text = f"{item.title} {item.summary}".lower()
    if "quote" in text:
        return Layout.quote
    if any(word in text for word in ("data", "metric", "number", "compare")):
        return Layout.two_column
    return Layout.single_column


async def create_card(
    outline: Outline,
    item: OutlineItem,
    settings: GenerationSettings,
    session: AsyncSession | None = None,
) -> Card:
    # The fallback is intentionally deterministic: a failed model call never removes
    # a card from a partially generated presentation.
    fallback = Card(
        id=item.id,
        title=item.title,
        layout=_fallback_layout(item),
        blocks=[
            {"type": "heading", "text": item.title},
            {"type": "paragraph", "text": item.summary},
            {
                "type": "bullets",
                "items": [
                    f"Context for {item.title}",
                    f"Designed for {settings.audience}",
                    "Turn this idea into an actionable next step",
                ],
            },
        ],
    )
    if session is None:
        return fallback
    config = await load_call_config(session, "ollama")
    if not config:
        return fallback
    rendered = _PROMPTS.get_template("card.jinja2").render(
        outline=outline, item=item, settings=settings, layouts=[layout.value for layout in Layout]
    )
    try:
        candidate = await generate_structured(Card, [{"role": "user", "content": rendered}], config)
        # Never trust an invalid or unknown layout hint; Pydantic has already
        # validated known enum values and deterministic fallback handles errors.
        return candidate.model_copy(update={"id": item.id})
    except Exception:
        return fallback


async def generate_cards(
    outline: Outline, settings: GenerationSettings, session: AsyncSession | None = None
) -> list[Card]:
    # A single SQLAlchemy AsyncSession cannot service concurrent model lookups.
    # Sequential local generation is also the safe default for weak hardware.
    if session is not None:
        return [await create_card(outline, item, settings, session) for item in outline.items]
    semaphore = asyncio.Semaphore(settings.concurrency)

    async def one(item: OutlineItem) -> Card:
        async with semaphore:
            return await create_card(outline, item, settings, session)

    return list(await asyncio.gather(*(one(item) for item in outline.items)))
