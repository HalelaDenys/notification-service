from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
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


class TelegramNotificationSchema(BaseNotificationSchema):
    type: Literal["telegram"]
    chat_id: Annotated[int, Field(gt=0, description="Chat ID")]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "telegram",
                "chat_id": 123456789,
                "message": "Hello from Telegram",
            }
        }
    )


NotificationRequestSchema = Annotated[
    EmailNotificationSchema | TelegramNotificationSchema,
    Field(discriminator="type"),
]


class DLQSchema(BaseModel):
    recipient: EmailStr
    error: str
    payload: dict
