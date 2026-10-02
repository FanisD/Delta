from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImageJobRecord(Base):
    __tablename__ = "image_jobs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    prompt: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    asset_id: Mapped[str | None] = mapped_column(String(120))
    error: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
