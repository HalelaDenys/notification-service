from enum import StrEnum


class ChannelEnum(StrEnum):
    SMTP = "smtp"
    TELEGRAM = "telegram"
    SLACK = "slack"


class StatusEnum(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    DLQ = "dlq"
    CANCELLED = "cancelled"


class StatusActionEnum(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
