from sqlalchemy.ext.asyncio import AsyncSession

from core import RetryPolicy, settings
from core.exceptions import RetryableError
from infrastructure import DBHelper, redis_client
from infrastructure.http_clients.slack.client import SlackClient
from infrastructure.http_clients.telegram.client import TelegramClient
from infrastructure.smtp.client import create_smtp_client
from repositories.notify_attempt_repo import NotificationAttemptRepository
from repositories.notify_repo import NotificationRepository
from services.dlq_service import DLQService
from services.file_work_service import FileWorkService
from services.notification_attempt_service import NotificationAttemptService
from services.notification_delivery_service import NotificationDeliveryService
from services.notification_service import NotificationService
from services.slack_notify_service import SlackNotifyService
from services.smtp_notify_service import SMTPNotifyService
from services.tg_notify_service import TelegramNotifyService


def create_smtp_notify_service() -> SMTPNotifyService:
    return SMTPNotifyService(
        smtp_client=create_smtp_client(),
    )


def create_telegram_notify_service(
    token: str = settings.tg.bot_token,
) -> TelegramNotifyService:
    return TelegramNotifyService(
        client=TelegramClient(token=token),
        file_service=FileWorkService(redis=redis_client),
    )


def create_slack_notify_service(
    token: str = settings.slack.bot_token,
) -> SlackNotifyService:
    return SlackNotifyService(
        client=SlackClient(token=token),
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


def create_notification_attempt_service(
    session: AsyncSession,
) -> NotificationAttemptService:
    return NotificationAttemptService(
        attempt_repo=NotificationAttemptRepository(
            session=session,
        ),
    )


def create_notification_delivery_service(
    db_helper: DBHelper,
    retryable_exceptions: tuple[type[RetryableError], ...],
    dlq_service: DLQService,
    stream_name: str,
) -> NotificationDeliveryService:
    return NotificationDeliveryService(
        retry_policy=RetryPolicy(
            retryable_exceptions=retryable_exceptions,
            max_attempts=5,
            base_delay=10,
            max_delay=10.0,
        ),
        notification_service_factory=create_notification_service,
        attempt_service_factory=create_notification_attempt_service,
        db_helper=db_helper,
        dlq_service=dlq_service,
        stream_name=stream_name,
    )
