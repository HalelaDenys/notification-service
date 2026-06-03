import pytest

from tests.e2e.conftest import wait_for_emails


class TestSmtpE2E:
    @pytest.mark.asyncio
    async def test_plain_email_delivered_to_maildev(
        self,
        async_client,
        email_payload_no_content,
    ):
        response = await async_client.post(
            "/api/v1/notifications", json=email_payload_no_content.model_dump()
        )

        assert response.status_code == 202

        emails = await wait_for_emails(count=1)

        assert len(emails) == 1

        email = emails[0]
        assert "text/plain" in email["headers"]["content-type"]
        assert email["subject"] == email_payload_no_content.subject
        assert email["to"][0]["address"] == email_payload_no_content.recipient
        assert email_payload_no_content.message in email["text"]

    @pytest.mark.asyncio
    async def test_html_email_delivered_to_maildev(
        self,
        async_client,
        email_payload_with_content,
    ):
        response = await async_client.post(
            "/api/v1/notifications", json=email_payload_with_content.model_dump()
        )

        assert response.status_code == 202
        emails = await wait_for_emails(count=1)

        email = emails[0]
        assert "multipart/alternative" in email["headers"]["content-type"]
        assert email["subject"] == email_payload_with_content.subject
        assert email["to"][0]["address"] == email_payload_with_content.recipient

        context = email_payload_with_content.context
        assert email_payload_with_content.message in email["html"]
        assert context.title in email["html"]
        assert context.action_text in email["html"]
        assert context.action_url in email["html"]
        assert context.preheader in email["html"]
