import pytest

from schemas.notify_schema import EmailContextSchema, EmailNotificationSchema
from services.stmp_notiy_service import STMPNotifyService


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


# SMTPNotifyService fixture
@pytest.fixture()
def smtp_service(fake_smtp_client):
    return STMPNotifyService(smtp_client=fake_smtp_client)


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
