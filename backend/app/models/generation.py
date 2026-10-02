from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class GenerationJobRecord(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    prompt: Mapped[str] = mapped_column(String(12000), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    outline: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    cards: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    errors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(nullable=False, default=0)
    deck_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
