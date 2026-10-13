class ApplicationException(Exception):
    """Base exception for the application."""

    def __init__(self, message: str):
        super().__init__(message)


class RetryException(ApplicationException):
    """Raised when all retry attempts are exhausted."""


class RetryableError(ApplicationException):
    """Transient error — the send can be retried."""


class NonRetryableError(ApplicationException):
    """Permanent error — retrying will not help."""


class SMTPException(ApplicationException):
    """Base SMTP exception."""


class SMTPClientException(SMTPException):
    """Base SMTP exception, kept for backward compatibility."""


class SMTPTransientError(SMTPClientException, RetryableError):
    """Connection timeout, 4xx SMTP codes, network issues."""


class SMTPPermanentError(SMTPClientException, NonRetryableError):
    """Invalid recipient, 5xx SMTP codes ('user unknown'), bad auth."""


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


class NotificationNotFoundError(RepositoryError):
    """Raised when a notification does not exist."""


class TelegramException(ApplicationException):
    """Base Telegram exception."""


class TelegramTransientError(TelegramException, RetryableError):
    """Timeout, network error, 429 (rate limit), 5xx from Telegram API."""


class TelegramPermanentError(TelegramException, NonRetryableError):
    """chat not found, bot blocked by user, invalid token."""


class SlackException(ApplicationException):
    """Base Slack exception."""


class SlackTransientError(SlackException, RetryableError):
    """Timeout, network error, 429 (rate limit), 5xx from Slack API."""


class SlackPermanentError(SlackException, NonRetryableError):
    """invalid webhook/token, channel_not_found."""


class NotificationBatchNotFoundError(RepositoryError):
    """Notification batch does not exist."""
