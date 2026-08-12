"""add unique constraint to Notification table

Revision ID: ea390dcacfe7
Revises: a6963432a5dd
Create Date: 2026-08-12 17:29:59.463558

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ea390dcacfe7"
down_revision: str | Sequence[str] | None = "a6963432a5dd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_notifications_idempotency_key"), "notifications", ["idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_notifications_idempotency_key"), "notifications", type_="unique"
    )
