from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints


class BaseNotificationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=10, max_length=300),
    ]


class EmailNotificationSchema(BaseNotificationSchema):
    type: Literal["email"]
    recipient: EmailStr
    subject: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
    ]


class TelegramNotificationSchema(BaseNotificationSchema):
    type: Literal["telegram"]
    chat_id: Annotated[int, Field(gt=0, description="Chat ID")]


NotificationRequestSchema = Annotated[
    EmailNotificationSchema | TelegramNotificationSchema,
    Field(discriminator="type"),
]
