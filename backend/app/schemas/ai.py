from typing import Literal

from pydantic import BaseModel, Field


class AIEditRequest(BaseModel):
    deck_id: str
    card_id: str
    block_index: int = Field(ge=0)
    action: Literal["rewrite", "shorten", "expand", "translate", "tone"]
    instruction: str = Field(default="", max_length=500)


class AIEditResponse(BaseModel):
    text: str
    action: str
