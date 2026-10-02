"""Add persistent generation jobs.

Revision ID: 0003_generation_jobs
Revises: 0002_llm_provider_settings
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_generation_jobs"
down_revision: str | None = "0002_llm_provider_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("prompt", sa.String(length=12000), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("outline", sa.JSON(), nullable=True),
        sa.Column("cards", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("deck_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("generation_jobs")
