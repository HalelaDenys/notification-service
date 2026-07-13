from core import RetryPolicy, settings
from core import exceptions as exc
from infrastructure.slack.client import SlackClient
from infrastructure.smtp.client import create_smtp_client
from infrastructure.telegram.client import TelegramClient
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
    )


def create_slack_notify_service(
    token: str = settings.slack.bot_token,
) -> SlackNotifyService:
    return SlackNotifyService(
        client=SlackClient(token=token),
        retry_policy=RetryPolicy(exceptions=(exc.SlackClientException,)),
    )
