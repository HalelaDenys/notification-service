import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    UUID,
    VARCHAR,
    Enum,
    ForeignKey,
    Integer,
    MetaData,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core import settings
from schemas.notify_enums import ChannelEnum, StatusActionEnum, StatusEnum


class BaseModel(DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(
        naming_convention=settings.db.naming_convention,
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Notification(BaseModel):
    __tablename__ = "notifications"

    channel: Mapped[ChannelEnum] = mapped_column(
        Enum(
            ChannelEnum,
            values_callable=lambda enum: [e.value for e in enum],
            name="channel_enum_type",
        ),
        nullable=False,
    )

    recipient: Mapped[str] = mapped_column(
        VARCHAR(100), comment="Who are we sending this to"
    )

    subject: Mapped[str | None] = mapped_column(VARCHAR(150), nullable=True)
    message: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    payload: Mapped[JSONB | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[StatusEnum] = mapped_column(
        Enum(
            StatusEnum,
            values_callable=lambda enum: [e.value for e in enum],
            name="status_enum",
        ),
        default=StatusEnum.PENDING,
        server_default=text(f"'{StatusEnum.PENDING.value}'"),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, server_default=text("0"))
    provider_message_id: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        VARCHAR(255), nullable=True, unique=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class NotificationAttempt(BaseModel):
    __tablename__ = "notification_attempts"
    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "attempt",
        ),
    )

    notification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notifications.id"),
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    status: Mapped[StatusActionEnum] = mapped_column(
        Enum(
            StatusActionEnum,
            values_callable=lambda enum: [e.value for e in enum],
            name="status_action_enum",
        ),
    )
    error_message: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
    error_cause: Mapped[str] = mapped_column(VARCHAR, nullable=False)

    request_payload: Mapped[JSONB | None] = mapped_column(JSONB, nullable=True)
    response_payload: Mapped[JSONB | None] = mapped_column(JSONB, nullable=True)

    provider_message_id: Mapped[str | None] = mapped_column(VARCHAR(100), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
