"""add file_id column in Notification model

Revision ID: 217f799203cc
Revises: ea390dcacfe7
Create Date: 2026-08-15 17:06:55.846256

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "217f799203cc"
down_revision: str | Sequence[str] | None = "ea390dcacfe7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "notification_attempts",
        "error_cause",
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    op.add_column(
        "notifications", sa.Column("file_id", sa.VARCHAR(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("notifications", "file_id")
    op.alter_column(
        "notification_attempts",
        "error_cause",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
