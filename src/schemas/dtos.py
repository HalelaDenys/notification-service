from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateNotificationAttemptDTO:
    notify_id: UUID
    request_payload: dict
    attempt: int
    started_at: datetime
    finished_at: datetime
    status: str
    provider_message_id: str | None = None
    error_message: str | None = None
    error_cause: str | None = None


@dataclass(frozen=True, slots=True)
class FileMetadataDTO:
    file_id: str
    file_name: str
    content_type: str | None
    size: int | None


@dataclass(frozen=True, slots=True)
class FileDataDTO:
    content: bytes
    metadata: FileMetadataDTO


@dataclass(frozen=True, slots=True)
class BaseNotificationDTO:
    pass


NotificationDTO = TypeVar(
    "NotificationDTO",
    bound=BaseNotificationDTO,
)


@dataclass(frozen=True, slots=True)
class SMTPNotificationDTO(BaseNotificationDTO):
    recipient: str
    subject: str
    plain_content: str
    html_content: str | None = None


@dataclass(frozen=True, slots=True)
class TelegramNotificationDTO(BaseNotificationDTO):
    chat_id: int
    text: str
    filename: str | None = None
    content: bytes | None = None
    content_type: str | None = None
    caption: str | None = None
    parse_mode: str = "HTML"
    reply_markup: dict | None = None


@dataclass(frozen=True, slots=True)
class SlackNotificationDTO(BaseNotificationDTO):
    channel_id: str
    text: str
    file_name: str | None = None
    content: bytes | None = None
    file_size: int | None = None
