from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deck import DeckRecord, utc_now
from app.schemas.deck import DeckCreate

SEED_DECKS: list[dict[str, Any]] = [
    {
        "id": "demo-local-first",
        "title": "Why local-first tools matter",
        "theme": "ocean",
        "cards": [
            {
                "id": "local-title",
                "title": "Why local-first tools matter",
                "layout": "title",
                "blocks": [
                    {"type": "heading", "text": "Your ideas. Your machine.", "level": 1},
                    {
                        "type": "paragraph",
                        "text": "A short introduction to software that keeps you in control.",
                    },
                    {
                        "type": "image",
                        "prompt": "Soft blue abstract sunrise over a quiet desktop",
                        "alt": "Abstract blue sunrise illustration",
                    },
                ],
            },
            {
                "id": "local-advantages",
                "title": "The benefits",
                "layout": "three_column",
                "blocks": [
                    {"type": "heading", "text": "Designed around the person"},
                    {
                        "type": "columns",
                        "columns": [
                            {"title": "Private", "body": "Keep your work and data close."},
                            {"title": "Available", "body": "Stay productive without a connection."},
                            {
                                "title": "In control",
                                "body": "Choose the tools that fit your needs.",
                            },
                        ],
                    },
                ],
            },
            {
                "id": "local-proof",
                "title": "A useful reminder",
                "layout": "quote",
                "blocks": [
                    {
                        "type": "quote",
                        "text": (
                            "The best tools amplify your work without getting between you and it."
                        ),
                        "attribution": "A local-first principle",
                    }
                ],
            },
        ],
    },
    {
        "id": "demo-great-presentations",
        "title": "The anatomy of a clear presentation",
        "theme": "sunset",
        "cards": [
            {
                "id": "presentation-title",
                "title": "Make every card count",
                "layout": "title",
                "blocks": [
                    {"type": "heading", "text": "One idea. One clear card.", "level": 1},
                    {
                        "type": "paragraph",
                        "text": "A practical guide to making complex ideas easier to follow.",
                    },
                ],
            },
            {
                "id": "presentation-structure",
                "title": "A simple structure",
                "layout": "two_column",
                "blocks": [
                    {"type": "heading", "text": "Give your audience a map"},
                    {
                        "type": "bullets",
                        "items": [
                            "Start with the key message",
                            "Build one step at a time",
                            "End with a clear next action",
                        ],
                    },
                    {
                        "type": "stat",
                        "value": "1 idea",
                        "label": "per card",
                        "context": "A useful editing test, not a rigid rule.",
                    },
                ],
            },
            {
                "id": "presentation-timeline",
                "title": "Build momentum",
                "layout": "timeline",
                "blocks": [
                    {"type": "heading", "text": "From context to action"},
                    {
                        "type": "columns",
                        "columns": [
                            {"title": "Context", "body": "Why this matters now"},
                            {"title": "Insight", "body": "What the evidence shows"},
                            {"title": "Action", "body": "What to do next"},
                        ],
                    },
                ],
            },
        ],
    },
    {
        "id": "demo-thoughtful-data",
        "title": "Tell a thoughtful data story",
        "theme": "forest",
        "cards": [
            {
                "id": "data-title",
                "title": "Numbers need a narrative",
                "layout": "image_left",
                "blocks": [
                    {"type": "heading", "text": "Put the signal in context", "level": 1},
                    {
                        "type": "paragraph",
                        "text": "A chart is most useful when the audience knows what to notice.",
                    },
                    {
                        "type": "image",
                        "prompt": (
                            "Minimal forest-green abstract visualization with gentle rising lines"
                        ),
                        "alt": "Abstract green data visualization",
                    },
                ],
            },
            {
                "id": "data-chart",
                "title": "Show an illustrative trend",
                "layout": "image_right",
                "blocks": [
                    {"type": "heading", "text": "Make the comparison visible"},
                    {
                        "type": "chart",
                        "title": "Example engagement trend",
                        "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
                        "values": [24, 38, 31, 56],
                        "illustrative": True,
                    },
                ],
            },
            {
                "id": "data-table",
                "title": "Keep the detail readable",
                "layout": "single_column",
                "blocks": [
                    {"type": "heading", "text": "Show the numbers behind the story"},
                    {
                        "type": "table",
                        "headers": ["Signal", "What it may suggest"],
                        "rows": [
                            ["Steady growth", "A pattern worth investigating"],
                            ["One sharp peak", "Check for a special event"],
                        ],
                    },
                    {
                        "type": "quote",
                        "text": (
                            "Treat generated example figures as illustrations, "
                            "never as observed facts."
                        ),
                        "attribution": "Data storytelling reminder",
                    },
                ],
            },
        ],
    },
]


async def seed_decks(session: AsyncSession) -> None:
    existing_ids = set((await session.scalars(select(DeckRecord.id))).all())
    now = utc_now()
    for seed in SEED_DECKS:
        if seed["id"] in existing_ids:
            continue
        deck_data = {key: value for key, value in seed.items() if key != "id"}
        deck = DeckCreate.model_validate(deck_data)
        session.add(
            DeckRecord(
                id=seed["id"],
                title=deck.title,
                theme=deck.theme.value,
                document=deck.model_dump(mode="json"),
                created_at=now,
                updated_at=now,
            )
        )
    await session.commit()
