import pytest

from workers import smtp_worker


class TestSmtpWorkerFaststream:
    @pytest.mark.asyncio
    async def test_consumes_email_from_stream(
        self,
        patched_notify_service,
        test_smtp_broker,
        email_payload_no_content,
    ):
        await test_smtp_broker.publish(
            email_payload_no_content, stream=smtp_worker.STREAM_NAME
        )

        assert len(patched_notify_service.calls) == 1

        data = patched_notify_service.calls[0]
        assert data.message == email_payload_no_content.message
        assert data.recipient == email_payload_no_content.recipient
        assert data.subject == email_payload_no_content.subject
        assert data.context is None

    @pytest.mark.asyncio
    async def test_consumes_email_with_context(
        self,
        patched_notify_service,
        test_smtp_broker,
        email_payload_with_content,
    ):
        await test_smtp_broker.publish(
            email_payload_with_content, stream=smtp_worker.STREAM_NAME
        )

        assert len(patched_notify_service.calls) == 1

        data = patched_notify_service.calls[0]
        assert data.context is not None
        assert data.context.title == email_payload_with_content.context.title
        assert data.context.action_url == email_payload_with_content.context.action_url
