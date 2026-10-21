"""update NotificationBatch model

Revision ID: a6199ef13e3a
Revises: f22d96e8153c
Create Date: 2026-10-10 12:17:17.268455

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6199ef13e3a"
down_revision: str | Sequence[str] | None = "f22d96e8153c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_notification_batches_idempotency_key"),
        "notification_batches",
        ["idempotency_key"],
    )
    op.execute("ALTER TYPE status_enum ADD VALUE IF NOT EXISTS 'cancelled';")
    op.execute("ALTER TYPE status_enum ADD VALUE IF NOT EXISTS 'queued';")


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_notification_batches_idempotency_key"),
        "notification_batches",
        type_="unique",
    )
