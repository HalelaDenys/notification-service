from unittest.mock import AsyncMock

import aiosmtplib
import pytest
import pytest_asyncio

from infrastructure import SMTPClient
from schemas.notify_schema import EmailContextSchema, EmailNotificationSchema
from services.stmp_notiy_service import STMPNotifyService


# SMTPNotifyService fixture
class FakeSMTPClient:
    def __init__(self):
        self.calls = []

    async def send_email(self, **kwargs):
        self.calls.append(kwargs)


@pytest.fixture()
def fake_smtp_client():
    return FakeSMTPClient()


@pytest.fixture()
def smtp_service(fake_smtp_client):
    return STMPNotifyService(smtp_client=fake_smtp_client)


@pytest.fixture()
def plain_data() -> EmailNotificationSchema:
    return EmailNotificationSchema(
        type="email",
        recipient="test@example.com",
        subject="Test subject",
        message="Test plain message",
    )


@pytest.fixture()
def html_data() -> EmailNotificationSchema:
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


# SMTPClient fixture
@pytest_asyncio.fixture()
async def smtp_send_mock(monkeypatch) -> AsyncMock:
    smtp_send = AsyncMock()
    monkeypatch.setattr(aiosmtplib, "send", smtp_send)
    return smtp_send


@pytest_asyncio.fixture()
async def smtp_client() -> SMTPClient:
    return SMTPClient(
        host="localhost",
        port=1025,
        username="user",
        password="secret",
        use_tls=False,
        sender="admin@example.com",
        start_tls=True,
        timeout=5.0,
    )
