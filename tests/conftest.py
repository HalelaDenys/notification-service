import pytest

from core.exceptions import TelegramClientException
from core.retry_policy import RetryPolicy
from infrastructure.telegram.client import TelegramClient
from schemas.notify_schema import (
    EmailContextSchema,
    EmailNotificationSchema,
    InlineKeyboardButtonSchema,
    InlineKeyboardMarkupSchema,
    ReplyKeyboardMarkupSchema,
    TelegramNotificationSchema,
    TelegramWebAppSchema,
)
from services.smtp_notify_service import SMTPNotifyService
from services.tg_notify_service import TelegramNotifyService


@pytest.fixture()
def retry_policy():
    return RetryPolicy(max_attempts=1, base_delay=0, jitter=False)


# SMTP notification fixture
class FakeSMTPClient:
    def __init__(self):
        self.calls = []

    async def send_email(self, **kwargs):
        self.calls.append(kwargs)


@pytest.fixture()
def fake_smtp_client():
    return FakeSMTPClient()


class FakeNotifyService:
    def __init__(self):
        self.calls = []
        self.should_fail = False

    async def send(self, data):
        if self.should_fail:
            raise RuntimeError("SMTP service unavailable")

        self.calls.append(data)


@pytest.fixture()
def fake_notify_service():
    return FakeNotifyService()


@pytest.fixture()
def smtp_service(fake_smtp_client, retry_policy):
    return SMTPNotifyService(smtp_client=fake_smtp_client, retry_policy=retry_policy)


@pytest.fixture()
def email_payload_no_content() -> EmailNotificationSchema:
    return EmailNotificationSchema(
        type="email",
        recipient="test@example.com",
        subject="Test subject",
        message="Test plain message",
    )


@pytest.fixture()
def email_payload_with_content() -> EmailNotificationSchema:
    return EmailNotificationSchema(
        type="email",
        recipient="test@example.com",
        subject="Test subject",
        message="Test plain message",
        context=EmailContextSchema(
            title="Test title",
            action_url="https://example.com",
            action_text="Open It",
            preheader="Test preheader",
        ),
    )


# Telegram notification fixture

TOKEN = "test-token"
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


class FakeTelegramClient:
    def __init__(self):
        self.calls = []

    async def send_message(self, **kwargs):
        self.calls.append(kwargs)


@pytest.fixture()
def fake_tg_client():
    return FakeTelegramClient()


@pytest.fixture()
def retry_policy_with_retries() -> RetryPolicy:
    return RetryPolicy(
        max_attempts=3,
        base_delay=0,
        jitter=False,
        exceptions=(TelegramClientException,),
    )


@pytest.fixture()
def tg_service(fake_tg_client, retry_policy_with_retries):
    return TelegramNotifyService(
        client=fake_tg_client, retry_policy=retry_policy_with_retries
    )


@pytest.fixture()
def tg_client() -> TelegramClient:
    return TelegramClient(token=TOKEN, timeout=5.0)


@pytest.fixture()
def plain_data_tg() -> TelegramNotificationSchema:
    return TelegramNotificationSchema(
        type="telegram",
        chat_id=1234567890,
        message="telegram plain message",
    )


@pytest.fixture()
def data_with_inline_keyboard() -> TelegramNotificationSchema:
    return TelegramNotificationSchema(
        type="telegram",
        chat_id=1234567890,
        message="telegram plain message",
        reply_markup=InlineKeyboardMarkupSchema(
            inline_keyboard=[
                [
                    InlineKeyboardButtonSchema(
                        text="Open",
                        url="https://example.com",
                    ),
                    InlineKeyboardButtonSchema(
                        text="Close",
                        callback_data="close",
                    ),
                ],
                [
                    InlineKeyboardButtonSchema(
                        text="🚀 Open App",
                        web_app=TelegramWebAppSchema(url="https://app.example.com"),
                    )
                ],
            ]
        ),
    )


@pytest.fixture()
def data_with_reply_keyboard() -> TelegramNotificationSchema:
    return TelegramNotificationSchema(
        type="telegram",
        chat_id=1234567890,
        message="telegram plain message",
        reply_markup=ReplyKeyboardMarkupSchema(
            keyboard=[
                ["yes", "no"],
                ["close"],
            ]
        ),
    )
