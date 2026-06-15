from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
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
    type: Literal["email"]
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
                "type": "email",
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


class ReplyKeyboardMarkupSchema(BaseModel):
    keyboard: list[list[str]]
    resize_keyboard: bool = True
    one_time_keyboard: bool = True
    selective: bool = True


class InlineKeyboardButtonSchema(BaseModel):
    text: str
    callback_data: Annotated[str | None, Field(max_length=64)] = None
    url: str | None = None
    # web_app: dict | None = None

    @model_validator(mode="after")
    def validate_callback_and_url(self):
        if self.callback_data and self.url:
            raise ValueError("Button cannot have both callback_data and url")
        if not self.callback_data and not self.url:
            raise ValueError("Button must have either callback_data or url")
        return self


class InlineKeyboardMarkupSchema(BaseModel):
    inline_keyboard: list[list[InlineKeyboardButtonSchema]]


class TelegramNotificationSchema(BaseNotificationSchema):
    type: Literal["telegram"]
    chat_id: Annotated[int, Field(gt=0, description="Chat ID")]
    reply_markup: InlineKeyboardMarkupSchema | ReplyKeyboardMarkupSchema | None = None


NotificationRequestSchema = Annotated[
    EmailNotificationSchema | TelegramNotificationSchema,
    Field(discriminator="type"),
]


class DLQSchema(BaseModel):
    recipient: str
    source_stream: str
    error_type: str
    error: str
    error_cause: str | None = None
    payload: dict
    failed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
