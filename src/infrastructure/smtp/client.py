import logging
from email.message import EmailMessage

import aiosmtplib

from core import settings
from core.exceptions import SMTPPermanentError, SMTPTransientError
from schemas.dtos import SMTPNotificationDTO

logger = logging.getLogger(__name__)

# codes 4xx by SMTP transient (mailbox busy, throttling),
# 5xx - permanent (user unknown, mailbox not found, policy reject)
_TRANSIENT_RESPONSE_CODES = range(400, 500)

# aiosmtplib exceptions, which always indicate a temporary problem
_TRANSIENT_EXCEPTIONS = (
    aiosmtplib.SMTPConnectError,
    aiosmtplib.SMTPConnectTimeoutError,
    aiosmtplib.SMTPServerDisconnected,
    aiosmtplib.SMTPTimeoutError,
    OSError,  # DNS, connection refused, network unreachable
)

# aiosmtplib exceptions that always indicate a persistent problem
_PERMANENT_EXCEPTIONS = (
    aiosmtplib.SMTPRecipientsRefused,
    aiosmtplib.SMTPRecipientRefused,
    aiosmtplib.SMTPSenderRefused,
    aiosmtplib.SMTPAuthenticationError,
)


class SMTPClient:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        *,
        sender: str | None = None,
        start_tls: bool = False,
        timeout: float = 10.0,
    ) -> None:
        if use_tls and start_tls:
            raise ValueError("use_tls and start_tls cannot both be enabled")

        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._sender = sender or username
        self._start_tls = start_tls
        self._timeout = timeout
        self._client: aiosmtplib.SMTP | None = None

    async def connect(self) -> None:
        self._client = aiosmtplib.SMTP(
            hostname=self._host,
            port=self._port,
            use_tls=self._use_tls,
            start_tls=self._start_tls,
            timeout=self._timeout,
        )
        await self._client.connect()
        if self._start_tls:
            await self._client.starttls()
        await self._client.login(self._username, self._password)

    async def close(self) -> None:
        if self._client is not None:
            try:
                if self._client.is_connected:
                    await self._client.quit()
            finally:
                self._client = None

    async def send(self, notification_data: SMTPNotificationDTO) -> None:
        await self._send_email(
            recipient=notification_data.recipient,
            subject=notification_data.subject,
            plain_content=notification_data.plain_content,
            html_content=notification_data.html_content,
        )

    async def _send_email(
        self,
        recipient: str,
        subject: str,
        plain_content: str,
        html_content: str | None = None,
    ) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(plain_content, subtype="plain", charset="utf-8")
        if html_content is not None:
            message.add_alternative(html_content, subtype="html", charset="utf-8")

        try:
            if self._client is None or not self._client.is_connected:
                await self.connect()
            await self._client.send_message(message)
        except _PERMANENT_EXCEPTIONS as exc:
            raise SMTPPermanentError(
                f"Permanent failure sending email to '{recipient}': {exc}"
            ) from exc
        except aiosmtplib.SMTPResponseException as exc:
            if exc.code in _TRANSIENT_RESPONSE_CODES:
                raise SMTPTransientError(
                    f"Transient SMTP error ({exc.code}) "
                    f"for '{recipient}': {exc.message}"
                ) from exc
            raise SMTPPermanentError(
                f"Permanent SMTP error ({exc.code}) for '{recipient}': {exc.message}"
            ) from exc
        except _TRANSIENT_EXCEPTIONS as exc:
            self._client = None
            raise SMTPTransientError(
                f"Transient failure sending email to '{recipient}': {exc}"
            ) from exc
        except aiosmtplib.SMTPException as exc:
            logger.warning(
                "Unclassified SMTPException for %s, treating as transient: %s",
                recipient,
                exc,
            )
            self._client = None
            raise SMTPTransientError(
                f"Unclassified SMTP error for '{recipient}': {exc}"
            ) from exc


def create_smtp_client() -> SMTPClient:
    return SMTPClient(
        host=settings.smtp.host,
        port=settings.smtp.port,
        username=settings.smtp.username,
        password=settings.smtp.password,
        use_tls=settings.smtp.use_tls,
        sender=settings.smtp.sender,
        start_tls=settings.smtp.start_tls,
        timeout=settings.smtp.timeout,
    )
