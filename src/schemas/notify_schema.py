from datetime import UTC, datetime
from typing import Annotated, Literal, TypeAlias
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)


class BaseNotificationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=10, max_length=300),
    ]


# ---------------- SMTP SCHEMAS ----------------
class EmailContextSchema(BaseModel):
    title: str
    action_url: str | None = None
    action_text: Annotated[
        str | None,
        Field(min_length=3, max_length=15),
    ] = None
    preheader: str | None = None

    @field_validator("action_text")
    @classmethod
    def validate_action_text(cls, v):
        v = v.strip()
        if len(v) <= 3:
            raise ValueError("Action Text must be valid and longer than 3 chars")
        return v


class EmailNotificationSchema(BaseNotificationSchema):
    type: Literal["smtp"]
    # template_type: Literal["notification", "marketing", "system"]
    recipient: EmailStr
    subject: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]
    context: EmailContextSchema | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "smtp",
                "recipient": "user@example.com",
                "subject": "Account updated",
                "message": "Your account was updated successfully",
                "context": {
                    "title": "Security Notification",
                    "action_url": "https://example.com/account",
                    "action_text": "Open",
                    "preheader": "Account update",
                },
            }
        }
    )


# ------------------ TELEGRAM SCHEMAS -------------------
class ReplyKeyboardMarkupSchema(BaseModel):
    keyboard: list[list[str]]
    resize_keyboard: bool = True
    one_time_keyboard: bool = True
    selective: bool = True


class TelegramWebAppSchema(BaseModel):
    url: HttpUrl


class InlineKeyboardButtonSchema(BaseModel):
    text: str
    callback_data: Annotated[str | None, Field(max_length=64)] = None
    url: HttpUrl | None = None
    web_app: TelegramWebAppSchema | None = None

    @model_validator(mode="after")
    def validate_button(self):
        actions = [
            self.callback_data,
            self.url,
            self.web_app,
        ]

        if sum(action is not None for action in actions) != 1:
            raise ValueError(
                "Button must have exactly one action: callback_data, url or web_app"
            )

        return self


class InlineKeyboardMarkupSchema(BaseModel):
    inline_keyboard: list[list[InlineKeyboardButtonSchema]]


class TelegramNotificationSchema(BaseNotificationSchema):
    type: Literal["telegram"]
    chat_id: Annotated[int, Field(gt=0, description="Chat ID")]
    reply_markup: InlineKeyboardMarkupSchema | ReplyKeyboardMarkupSchema | None = None
    file_id: str | None = None


# ------------------- SLACK SCHEMAS -----------------------
class SlackNotificationSchema(BaseNotificationSchema):
    type: Literal["slack"]
    channel_id: Annotated[str, Field(min_length=10, max_length=25)]
    file_id: str | None = None


NotificationRequestSchema: TypeAlias = Annotated[
    EmailNotificationSchema | TelegramNotificationSchema | SlackNotificationSchema,
    Field(discriminator="type"),
]


# ================== WORKER REQUEST SCHEMAS ====================
class BaseSendMessageToBrokerSchema(BaseModel):
    notify_id: UUID


class SendEmailMessageToBrokerSchema(BaseSendMessageToBrokerSchema):
    notify_data: EmailNotificationSchema


class SendTelegramMessageToBrokerSchema(BaseSendMessageToBrokerSchema):
    notify_data: TelegramNotificationSchema


class SendSlackMessageToBrokerSchema(BaseSendMessageToBrokerSchema):
    notify_data: SlackNotificationSchema


SendMessageToBrokerSchemaType: TypeAlias = Annotated[
    EmailNotificationSchema | TelegramNotificationSchema | SlackNotificationSchema,
    Field(discriminator="type"),
]


class DLQMessageToBrokerSchema(BaseModel):
    original_data: dict
    error_message: str
    error_full_cause: str
    source_stream: str
    failed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )


# =============== NOTIFICATION BATCH SCHEMAS ===============
class BaseBatchNotificationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=10, max_length=300),
    ]


class BaseBatchRecipientSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------- SMTP BATCH SCHEMAS -----------------
class SMTPBatchRecipientSchema(BaseBatchRecipientSchema):
    recipient: EmailStr
    context: EmailContextSchema | None = None


class SMTPBatchNotificationRequestSchema(BaseBatchNotificationSchema):
    type: Literal["smtp"]
    subject: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=100)
    ]

    recipients: Annotated[
        list[SMTPBatchRecipientSchema], Field(min_length=1, max_length=10_000)
    ]

    @field_validator("recipients")
    @classmethod
    def validate_unique_recipients(
        cls,
        recipients: list[SMTPBatchRecipientSchema],
    ) -> list[SMTPBatchRecipientSchema]:
        seen = {r.recipient for r in recipients}

        if len(seen) != len(recipients):
            raise ValueError(
                "Duplicate recipients are not allowed in a single batch",
            )
        return recipients


# --------------- TELEGRAM BATCH SCHEMAS -----------------
class TelegramBatchRecipientSchema(BaseBatchRecipientSchema):
    chat_id: Annotated[int, Field(gt=0, description="Chat ID")]
    file_id: str | None = None


class TelegramBatchNotificationRequestSchema(BaseBatchNotificationSchema):
    type: Literal["telegram"]
    reply_markup: InlineKeyboardMarkupSchema | ReplyKeyboardMarkupSchema | None = None
    recipients: Annotated[
        list[TelegramBatchRecipientSchema], Field(min_length=1, max_length=10_000)
    ]

    @field_validator("recipients")
    @classmethod
    def validate_unique_recipients(
        cls,
        recipients: list[TelegramBatchRecipientSchema],
    ) -> list[TelegramBatchRecipientSchema]:
        seen = {r.chat_id for r in recipients}

        if len(seen) != len(recipients):
            raise ValueError(
                "Duplicate recipients are not allowed in a single batch",
            )
        return recipients


# --------------- SLACK BATCH SCHEMAS -----------------
class SlackBatchRecipientSchema(BaseBatchRecipientSchema):
    channel_id: Annotated[int, Field(gt=0, description="Channel ID")]
    file_id: str | None = None


class SlackBatchNotificationRequestSchema(BaseBatchNotificationSchema):
    type: Literal["slack"]
    recipients: Annotated[
        list[SlackBatchRecipientSchema],
        Field(min_length=1, max_length=10_000),
    ]

    @field_validator("recipients")
    @classmethod
    def validate_unique_recipients(
        cls,
        recipients: list[SlackBatchRecipientSchema],
    ) -> list[SlackBatchRecipientSchema]:
        seen = {r.channel_id for r in recipients}

        if len(seen) != len(recipients):
            raise ValueError(
                "Duplicate recipients are not allowed in a single batch",
            )
        return recipients


BatchNotificationRequestSchema = Annotated[
    SMTPBatchNotificationRequestSchema
    | TelegramBatchNotificationRequestSchema
    | SlackBatchNotificationRequestSchema,
    Field(discriminator="type"),
]


# ---------- BATCh RESPONSE SCHEMAS ----------
class BatchCreatedResponseSchema(BaseModel):
    batch_id: UUID
    total: int
    skipped_duplicates: int
    idempotent_replay: bool


class BatchStatusResponseSchema(BaseModel):
    batch_id: UUID
    total: int
    pending: int = 0
    queued: int = 0
    processing: int = 0
    sent: int = 0
    failed: int = 0
    dlq: int = 0
    cancelled: int = 0
    cancelled_at: str | None = None
