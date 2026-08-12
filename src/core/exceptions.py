class ApplicationException(Exception):
    """Base exception for the application."""

    def __init__(self, message: str):
        super().__init__(message)


class RetryException(ApplicationException):
    """Raised when all retry attempts are exhausted."""


class SMTPException(ApplicationException):
    """Base SMTP exception."""


class SMTPClientException(SMTPException):
    """SMTP client error."""


class TelegramException(ApplicationException):
    """Base Telegram exception."""


class TelegramClientException(TelegramException):
    """Telegram API/client error."""


class TGAdminChatIdException(TelegramException):
    """Admin chat ID is not configured or invalid."""


class SlackException(ApplicationException):
    """Base Slack exception."""


class SlackClientException(SlackException):
    """Slack client error."""


class SlackErrorChannelException(SlackException):
    """Slack error channel."""


class UnsupportedFileTypeError(ApplicationException):
    """Unsupported file type."""


class FileTooLargeError(ApplicationException):
    """File too large."""


class FileNotFoundOrExpiredError(ApplicationException):
    """File not found."""


class RepositoryError(ApplicationException):
    """Base repository error."""


class MultipleRowsFoundError(RepositoryError):
    """Raised when a unique lookup matches more than one row."""
