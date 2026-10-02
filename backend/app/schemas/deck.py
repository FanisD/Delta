from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


class Theme(StrEnum):
    ocean = "ocean"
    sunset = "sunset"
    forest = "forest"


class Layout(StrEnum):
    title_slide = "title"
    single_column = "single_column"
    two_column = "two_column"
    three_column = "three_column"
    image_left = "image_left"
    image_right = "image_right"
    quote = "quote"
    timeline = "timeline"


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
BodyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
LabelText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HeadingBlock(StrictModel):
    type: Literal["heading"]
    text: ShortText
    level: int = Field(default=2, ge=1, le=3)


class ParagraphBlock(StrictModel):
    type: Literal["paragraph"]
    text: BodyText


class BulletsBlock(StrictModel):
    type: Literal["bullets"]
    items: list[ShortText] = Field(min_length=1, max_length=12)


class ColumnContent(StrictModel):
    title: LabelText
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ColumnsBlock(StrictModel):
    type: Literal["columns"]
    columns: list[ColumnContent] = Field(min_length=2, max_length=3)


class QuoteBlock(StrictModel):
    type: Literal["quote"]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    attribution: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] | None = (
        None
    )


class StatBlock(StrictModel):
    type: Literal["stat"]
    value: LabelText
    label: LabelText
    context: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None


class TableBlock(StrictModel):
    type: Literal["table"]
    headers: list[LabelText] = Field(min_length=1, max_length=6)
    rows: list[list[Annotated[str, StringConstraints(max_length=300)]]] = Field(
        min_length=1, max_length=20
    )

    @model_validator(mode="after")
    def validate_row_widths(self) -> TableBlock:
        if any(len(row) != len(self.headers) for row in self.rows):
            raise ValueError("Each table row must match the number of headers")
        return self


class ImageBlock(StrictModel):
    type: Literal["image"]
    prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    asset_id: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
        | None
    ) = None
    alt: Annotated[str, StringConstraints(strip_whitespace=True, max_length=240)] = ""


class ChartBlock(StrictModel):
    type: Literal["chart"]
    title: LabelText
    labels: list[LabelText] = Field(min_length=2, max_length=12)
    values: list[Annotated[float, Field(ge=0, le=1_000_000_000_000, allow_inf_nan=False)]] = Field(
        min_length=2, max_length=12
    )
    illustrative: bool = True

    @model_validator(mode="after")
    def validate_series(self) -> ChartBlock:
        if len(self.labels) != len(self.values):
            raise ValueError("Chart labels and values must have the same number of items")
        return self


class MermaidBlock(StrictModel):
    type: Literal["mermaid"]
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    caption: LabelText | None = None


class IconBlock(StrictModel):
    type: Literal["icon"]
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z][A-Za-z0-9-]{0,48}$")
    ]
    label: LabelText | None = None


Block = Annotated[
    HeadingBlock
    | ParagraphBlock
    | BulletsBlock
    | ColumnsBlock
    | QuoteBlock
    | StatBlock
    | TableBlock
    | ImageBlock
    | ChartBlock
    | MermaidBlock
    | IconBlock,
    Field(discriminator="type"),
]


class Card(StrictModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=80)
    title: ShortText
    layout: Layout
    blocks: list[Block] = Field(min_length=1, max_length=30)


class DeckCreate(StrictModel):
    title: ShortText
    theme: Theme = Theme.ocean
    cards: list[Card] = Field(min_length=1, max_length=100)


class DeckUpdate(StrictModel):
    title: ShortText | None = None
    theme: Theme | None = None
    cards: list[Card] | None = Field(default=None, min_length=1, max_length=100)
    version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_patch(self) -> DeckUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("Fields cannot be null")
        return self


class DeckDocument(DeckCreate):
    theme: Theme
    id: str
    created_at: datetime
    updated_at: datetime
    version: int = Field(default=1, ge=1)
