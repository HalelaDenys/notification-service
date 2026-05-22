import logging
from email.message import EmailMessage

import aiosmtplib

from core import settings

logger = logging.getLogger(__name__)


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

    async def send_email(
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
            await aiosmtplib.send(
                message,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                use_tls=self._use_tls,
                start_tls=self._start_tls,
                timeout=self._timeout,
            )
        except (aiosmtplib.SMTPException, OSError):
            logger.exception(
                "Email send failed: recipient=%s host=%s port=%s",
                recipient,
                self._host,
                self._port,
            )
            raise


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
