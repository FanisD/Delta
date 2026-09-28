import pytest
from pydantic import ValidationError

from app.schemas.deck import (
    ChartBlock,
    DeckCreate,
    HeadingBlock,
    ParagraphBlock,
    TableBlock,
)


def test_deck_accepts_discriminated_block_types() -> None:
    deck = DeckCreate.model_validate(
        {
            "title": "A small deck",
            "theme": "ocean",
            "cards": [
                {
                    "title": "Welcome",
                    "layout": "title",
                    "blocks": [
                        {"type": "heading", "text": "Start here"},
                        {"type": "paragraph", "text": "A short introduction."},
                    ],
                }
            ],
        }
    )

    assert isinstance(deck.cards[0].blocks[0], HeadingBlock)
    assert isinstance(deck.cards[0].blocks[1], ParagraphBlock)


def test_block_text_is_length_limited() -> None:
    with pytest.raises(ValidationError):
        HeadingBlock(type="heading", text="x" * 241)


def test_invalid_theme_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DeckCreate.model_validate(
            {
                "title": "Invalid theme",
                "theme": "unknown",
                "cards": [
                    {
                        "title": "Welcome",
                        "layout": "title",
                        "blocks": [{"type": "heading", "text": "Hello"}],
                    }
                ],
            }
        )


def test_chart_labels_and_values_must_have_matching_lengths() -> None:
    with pytest.raises(ValidationError):
        ChartBlock(
            type="chart",
            title="Example chart",
            labels=["A", "B"],
            values=[1],
        )


def test_table_rows_must_match_header_count() -> None:
    with pytest.raises(ValidationError):
        TableBlock(
            type="table",
            headers=["Signal", "Meaning"],
            rows=[["Only one cell"]],
        )
