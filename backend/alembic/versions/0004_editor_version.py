"""Add optimistic versioning for editor saves."""

from alembic import op
import sqlalchemy as sa

revision = "0004_editor_version"
down_revision = "0003_generation_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("decks", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("decks", "version")
