from core import RetryPolicy, settings
from core import exceptions as exc
from infrastructure.smtp.client import create_smtp_client
from infrastructure.telegram.client import TelegramClient
from services.smtp_notify_service import SMTPNotifyService
from services.tg_notify_service import TelegramNotifyService


def create_smtp_notify_service() -> SMTPNotifyService:
    return SMTPNotifyService(
        smtp_client=create_smtp_client(),
        retry_policy=RetryPolicy(exceptions=(exc.SMTPClientException,)),
    )


def create_telegram_notify_service(
    token: str = settings.tg.token,
) -> TelegramNotifyService:
    return TelegramNotifyService(
        client=TelegramClient(token=token),
        retry_policy=RetryPolicy(exceptions=(exc.TelegramClientException,)),
    )
