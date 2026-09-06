from enum import StrEnum


class ChannelEnum(StrEnum):
    SMTP = "smtp"
    TELEGRAM = "telegram"
    SLACK = "slack"


class StatusEnum(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    DLQ = "dlq"


class StatusActionEnum(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
