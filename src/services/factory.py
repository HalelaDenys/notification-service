from core import RetryPolicy, settings
from infrastructure.smtp.client import create_smtp_client
from infrastructure.telegram.client import TelegramClient
from schemas.notify_schema import EmailNotificationSchema, TelegramNotificationSchema
from services.protocols import NotificationSender
from services.smtp_notify_service import SMTPNotifyService
from services.tg_notify_service import TelegramNotifyService


def create_smtp_notify_service() -> NotificationSender[EmailNotificationSchema]:
    return SMTPNotifyService(
        smtp_client=create_smtp_client(),
        retry_policy=RetryPolicy(),
    )


def create_telegram_notify_service(
    token: str = settings.tg.token,
) -> NotificationSender[TelegramNotificationSchema]:
    return TelegramNotifyService(
        client=TelegramClient(token=token),
        retry_policy=RetryPolicy(),
    )
