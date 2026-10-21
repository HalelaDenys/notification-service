class ApplicationException(Exception):
    """Base exception for the application."""


# -------------- SEND ERRORS (what the worker classifies) ----------------
class NotificationError(ApplicationException):
    """Base for errors raised while sending; carries diagnostic fields."""

    def __init__(
        self,
        msg: str,
        *,
        status_code: int | None = None,
        cause_type: str | None = None,
    ) -> None:
        super().__init__(msg)
        self.status_code = status_code
        self.cause_type = cause_type


class RetryableError(NotificationError):
    """Transient error: the send can be retried."""

    def __init__(self, msg: str, *, retry_after: int | None = None, **kwargs) -> None:
        super().__init__(msg, **kwargs)
        self.retry_after = retry_after


class NonRetryableError(NotificationError):
    """Permanent error: retrying will not help."""


class HTTPStatusClassificationError(NonRetryableError):
    """HTTP status code that is neither known-transient nor known-permanent."""


class RetryException(ApplicationException):
    """Raised when all retry attempts are exhausted.

    Raise it with the last error as the cause:
        raise RetryException("...", attempts=n) from last_error
    """


# ------------------ CONFIGURATION ERROR ----------------------
class ConfigurationError(NonRetryableError):
    """Missing or invalid configuration: retrying will not help."""


# ------------------ SMTP ERROR ----------------------
class SMTPException(ApplicationException):
    """Base SMTP exception."""


class SMTPClientException(SMTPException):
    """Base SMTP exception, kept for backward compatibility."""


class SMTPTransientError(SMTPClientException, RetryableError):
    """Connection timeout, 4xx SMTP codes, network issues."""


class SMTPPermanentError(SMTPClientException, NonRetryableError):
    """Invalid recipient, 5xx SMTP codes ('user unknown'), bad auth."""


# --------------- TELEGRAM ERROR -------------------
class TelegramException(ApplicationException):
    """Base Telegram exception."""


class TelegramClientException(TelegramException, NonRetryableError):
    """Telegram API/client error."""


class TelegramTransientError(TelegramException, RetryableError):
    """Timeout, network error, 408/429/5xx from Telegram API."""


class TelegramPermanentError(TelegramException, NonRetryableError):
    """Invalid token, chat not found, bot blocked by user, bad request."""


class TGAdminChatIdException(TelegramException, ConfigurationError):
    """Admin chat ID is not configured or invalid."""


# --------------- SLACK ERROR -------------------
class SlackException(ApplicationException):
    """Base Slack exception."""


class SlackClientException(SlackException, NonRetryableError):
    """Slack client error."""


class SlackTransientError(SlackException, RetryableError):
    """Timeout, network error, ratelimited, 5xx / internal_error from Slack API."""


class SlackPermanentError(SlackException, NonRetryableError):
    """Invalid token, channel_not_found, not_in_channel, is_archived."""


class SlackErrorChannelException(SlackException, ConfigurationError):
    """Slack error channel is not configured or invalid."""


# ------------------ FILE ERROR ----------------------
class UnsupportedFileTypeError(NonRetryableError):
    """Unsupported file type."""


class FileTooLargeError(NonRetryableError):
    """File too large."""


class FileNotFoundOrExpiredError(NonRetryableError):
    """File not found or expired."""


# -------------- REPO DB ERROR ----------------
class RepositoryError(ApplicationException):
    """Base repository error."""


class MultipleRowsFoundError(RepositoryError):
    """Raised when a unique lookup matches more than one row."""


class NotificationNotFoundError(RepositoryError):
    """Raised when a notification does not exist."""


class NotificationBatchNotFoundError(RepositoryError):
    """Notification batch does not exist."""
