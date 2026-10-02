from datetime import UTC, datetime

import pytest

from app.schemas.agent import (
    AddCardOperation,
    DeleteCardOperation,
    SetThemeOperation,
)
from app.schemas.deck import Card, DeckDocument, Layout, Theme
from app.services.agent import AgentOperationError, apply_operations


def deck() -> DeckDocument:
    return DeckDocument(
        id="deck",
        title="Demo",
        theme=Theme.ocean,
        cards=[
            Card(
                id="one",
                title="One",
                layout=Layout.title_slide,
                blocks=[
                    {"type": "heading", "text": "One", "level": 1},
                ],
            )
        ],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_agent_applies_operations_to_copy_and_preserves_source() -> None:
    source = deck()
    added = Card(
        id="two",
        title="Two",
        layout=Layout.single_column,
        blocks=[
            {"type": "paragraph", "text": "Body"},
        ],
    )
    result = apply_operations(
        source,
        [
            AddCardOperation(op="add_card", card=added),
            SetThemeOperation(op="set_theme", theme=Theme.forest),
        ],
    )
    assert len(result.deck.cards) == 2
    assert result.deck.theme == Theme.forest
    assert len(source.cards) == 1


def test_delete_requires_confirmation() -> None:
    source = deck()
    source.cards.append(
        Card(
            id="two",
            title="Two",
            layout=Layout.single_column,
            blocks=[
                {"type": "paragraph", "text": "Body"},
            ],
        )
    )
    result = apply_operations(
        source,
        [
            DeleteCardOperation(op="delete_card", card_id="one"),
        ],
    )
    assert result.requires_confirmation
    applied = apply_operations(
        source,
        [
            DeleteCardOperation(op="delete_card", card_id="one", confirmed=True),
        ],
    )
    assert len(applied.deck.cards) == 1
    with pytest.raises(AgentOperationError):
        apply_operations(
            deck(),
            [
                DeleteCardOperation(op="delete_card", card_id="one", confirmed=True),
            ],
        )
