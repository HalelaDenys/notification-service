from sqlalchemy.ext.asyncio import AsyncSession

from core import RetryPolicy, settings
from core import exceptions as exc
from infrastructure import redis_client
from infrastructure.slack.client import SlackClient
from infrastructure.smtp.client import create_smtp_client
from infrastructure.telegram.client import TelegramClient
from repositories.notify_repo import NotificationRepository
from services.file_work_service import FileWorkService
from services.notification_service import NotificationService
from services.slack_notify_service import SlackNotifyService
from services.smtp_notify_service import SMTPNotifyService
from services.tg_notify_service import TelegramNotifyService


def create_smtp_notify_service() -> SMTPNotifyService:
    return SMTPNotifyService(
        smtp_client=create_smtp_client(),
        retry_policy=RetryPolicy(exceptions=(exc.SMTPClientException,)),
    )


def create_telegram_notify_service(
    token: str = settings.tg.bot_token,
) -> TelegramNotifyService:
    return TelegramNotifyService(
        client=TelegramClient(token=token),
        retry_policy=RetryPolicy(exceptions=(exc.TelegramClientException,)),
        file_service=FileWorkService(redis=redis_client),
    )


def create_slack_notify_service(
    token: str = settings.slack.bot_token,
) -> SlackNotifyService:
    return SlackNotifyService(
        client=SlackClient(token=token),
        retry_policy=RetryPolicy(exceptions=(exc.SlackClientException,)),
        file_service=FileWorkService(redis=redis_client),
    )


def create_notification_service(
    session: AsyncSession,
) -> NotificationService:
    return NotificationService(
        notify_repo=NotificationRepository(
            session=session,
        ),
    )
