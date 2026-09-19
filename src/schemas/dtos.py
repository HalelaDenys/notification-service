from dataclasses import dataclass
from datetime import datetime
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
