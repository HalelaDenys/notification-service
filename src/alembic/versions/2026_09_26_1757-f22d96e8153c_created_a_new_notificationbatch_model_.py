"""created a new NotificationBatch model and created an index for the Notification model

Revision ID: f22d96e8153c
Revises: 217f799203cc
Create Date: 2026-09-26 17:57:55.262039

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f22d96e8153c"
down_revision: str | Sequence[str] | None = "217f799203cc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_batches",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("idempotency_key", sa.VARCHAR(length=255), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("cancelled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_batches")),
    )
    op.add_column("notifications", sa.Column("batch_id", sa.UUID(), nullable=True))
    op.create_index(
        "idx_notifications_batch_status",
        "notifications",
        ["batch_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_notifications_pending_retry",
        "notifications",
        ["next_retry_at"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_foreign_key(
        op.f("fk_notifications_batch_id_notification_batches"),
        "notifications",
        "notification_batches",
        ["batch_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_notifications_batch_id_notification_batches"),
        "notifications",
        type_="foreignkey",
    )
    op.drop_index(
        "idx_notifications_pending_retry",
        table_name="notifications",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_index("idx_notifications_batch_status", table_name="notifications")
    op.drop_column("notifications", "batch_id")
    op.drop_table("notification_batches")
