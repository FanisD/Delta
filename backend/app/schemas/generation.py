from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.deck import Card


class GenerationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_count: int = Field(default=6, ge=1, le=30)
    tone: str = Field(default="clear", min_length=1, max_length=80)
    language: str = Field(default="English", min_length=1, max_length=80)
    audience: str = Field(default="general", min_length=1, max_length=160)
    density: Literal["concise", "balanced", "detailed"] = "balanced"
    concurrency: int = Field(default=3, ge=1, le=8)


class OutlineItem(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(min_length=1, max_length=1000)


class Outline(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    items: list[OutlineItem] = Field(min_length=1, max_length=30)


class OutlineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=12000)
    settings: GenerationSettings = Field(default_factory=GenerationSettings)


class GenerationJobCreate(OutlineRequest):
    outline: Outline | None = None


class GenerationJobStatus(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "partial", "failed"]
    progress: int = Field(ge=0, le=100)
    outline: Outline | None = None
    cards: list[Card] = []
    errors: list[str] = []
    deck_id: str | None = None
    created_at: datetime
    updated_at: datetime


class RegenerateCardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str | None = Field(default=None, max_length=12000)
    settings: GenerationSettings | None = None
