"""first migration

Revision ID: a6963432a5dd
Revises:
Create Date: 2026-08-10 17:42:17.978963

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6963432a5dd"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column(
            "channel",
            sa.Enum("smtp", "telegram", "slack", name="channel_enum_type"),
            nullable=False,
        ),
        sa.Column(
            "recipient",
            sa.VARCHAR(length=100),
            nullable=False,
            comment="Who are we sending this to",
        ),
        sa.Column("subject", sa.VARCHAR(length=150), nullable=True),
        sa.Column("message", sa.VARCHAR(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "processing", "sent", "failed", "dlq", name="status_enum"
            ),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("error_message", sa.VARCHAR(length=255), nullable=True),
        sa.Column(
            "retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("provider_message_id", sa.VARCHAR(length=100), nullable=True),
        sa.Column("idempotency_key", sa.VARCHAR(length=255), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_table(
        "notification_attempts",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("notification_id", sa.UUID(), nullable=False),
        sa.Column("attempt", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("success", "failed", name="status_action_enum"),
            nullable=False,
        ),
        sa.Column("error_message", sa.VARCHAR(length=255), nullable=True),
        sa.Column("error_cause", sa.VARCHAR(), nullable=False),
        sa.Column(
            "request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("provider_message_id", sa.VARCHAR(length=100), nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name=op.f("fk_notification_attempts_notification_id_notifications"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notification_attempts")),
        sa.UniqueConstraint(
            "notification_id",
            "attempt",
            name=op.f("uq_notification_attempts_notification_id_attempt"),
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_attempts")
    op.drop_table("notifications")
