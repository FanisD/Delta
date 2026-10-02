from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.deck import Block, Card, DeckDocument, Layout, Theme


class AgentOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: str


class AddCardOperation(AgentOperation):
    op: Literal["add_card"]
    card: Card
    index: int | None = Field(default=None, ge=0, le=100)


class UpdateBlockOperation(AgentOperation):
    op: Literal["update_block"]
    card_id: str = Field(min_length=1, max_length=80)
    block_index: int = Field(ge=0, le=29)
    block: Block


class MoveCardOperation(AgentOperation):
    op: Literal["move_card"]
    card_id: str = Field(min_length=1, max_length=80)
    to_index: int = Field(ge=0, le=99)


class DeleteCardOperation(AgentOperation):
    op: Literal["delete_card"]
    card_id: str = Field(min_length=1, max_length=80)
    confirmed: bool = False


class SetLayoutOperation(AgentOperation):
    op: Literal["set_layout"]
    card_id: str = Field(min_length=1, max_length=80)
    layout: Layout


class SetThemeOperation(AgentOperation):
    op: Literal["set_theme"]
    theme: Theme


EditOperation = Annotated[
    AddCardOperation
    | UpdateBlockOperation
    | MoveCardOperation
    | DeleteCardOperation
    | SetLayoutOperation
    | SetThemeOperation,
    Field(discriminator="op"),
]


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deck: DeckDocument
    message: str = Field(min_length=1, max_length=4000)
    operations: list[EditOperation] | None = Field(default=None, max_length=20)
    confirm_deletions: bool = False


class AgentPreview(BaseModel):
    deck: DeckDocument
    operations: list[EditOperation]
    requires_confirmation: bool = False
    warnings: list[str] = []
