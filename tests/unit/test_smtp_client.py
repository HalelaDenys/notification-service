from unittest.mock import AsyncMock

import aiosmtplib
import pytest

from infrastructure.smtp.client import SMTPClient


class TestSMTPClient:
    def test_smtp_client_rejects_tls_and_start_tls_together(self):
        with pytest.raises(
            ValueError, match="use_tls and start_tls cannot both be enabled"
        ):
            SMTPClient(
                host="localhost",
                port=1025,
                username="test_user",
                password="password",
                use_tls=True,
                start_tls=True,
            )

    @pytest.mark.asyncio
    async def test_send_email_passes_correct_smtp_kwargs(
        self,
        smtp_client,
        smtp_send_mock,
    ):
        await smtp_client.send_email(
            recipient="test@example.com",
            subject="test subject",
            plain_content="hello",
        )

        smtp_send_mock.assert_awaited_once()

        kwargs = smtp_send_mock.await_args.kwargs

        assert kwargs["hostname"] == "localhost"
        assert kwargs["port"] == 1025
        assert kwargs["start_tls"] is True
        assert kwargs["timeout"] == 5.0

    @pytest.mark.asyncio
    async def test_send_email_builds_plain_message(
        self,
        smtp_send_mock,
        smtp_client,
    ):
        await smtp_client.send_email(
            recipient="test@example.com",
            subject="test subject",
            plain_content="test plain content",
        )

        smtp_send_mock.assert_awaited_once()

        message = smtp_send_mock.await_args.args[0]

        assert message["From"] == "admin@example.com"
        assert message["To"] == "test@example.com"
        assert message["Subject"] == "test subject"
        assert message.get_content().strip() == "test plain content"
        assert message.get_content_type() == "text/plain"

    @pytest.mark.asyncio
    async def test_send_email_builds_html_message(
        self,
        smtp_send_mock,
        smtp_client,
    ):
        await smtp_client.send_email(
            recipient="test@example.com",
            subject="Confirm your email",
            plain_content="Please confirm your email address",
            html_content="<h1>Please confirm your email address</h1>",
        )

        smtp_send_mock.assert_awaited_once()

        message = smtp_send_mock.await_args.args[0]

        assert message["From"] == "admin@example.com"
        assert message.get_content_type() == "multipart/alternative"
        assert (
            message.get_body(("plain",)).get_content().strip()
            == "Please confirm your email address"
        )
        assert (
            message.get_body(("html",)).get_content().strip()
            == "<h1>Please confirm your email address</h1>"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error",
        [
            aiosmtplib.SMTPException("connection refused"),
            OSError("network unreachable"),
        ],
    )
    async def test_send_email_reraises_send_error(
        self, smtp_client, monkeypatch, error: Exception
    ):
        monkeypatch.setattr(aiosmtplib, "send", AsyncMock(side_effect=error))

        with pytest.raises(type(error), match=str(error)):
            await smtp_client.send_email(
                recipient="test@example.com",
                subject="test error subject",
                plain_content="test error plain content",
            )

    @pytest.mark.asyncio()
    async def test_send_email_raises_on_type_error(
        self,
        smtp_client,
    ):
        with pytest.raises(TypeError):
            await smtp_client.send_email(
                recipient="test@example.com",
                subject="test error subject",
                # no plain_content
            )
