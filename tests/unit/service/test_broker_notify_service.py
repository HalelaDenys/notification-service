import pytest
from faststream.exceptions import FastStreamException


class TestBrokerNotifyService:
    @pytest.mark.asyncio
    async def test_publish_to_current_stream(
        self,
        mock_broker,
        broker_notify_service,
        email_payload_no_content,
    ):
        await broker_notify_service.send(email_payload_no_content)

        mock_broker.publish.assert_awaited_once_with(
            email_payload_no_content,
            stream="notifications.email",
        )

    @pytest.mark.asyncio
    async def test_reraises_faststream_exception(
        self,
        mock_broker,
        broker_notify_service,
        email_payload_no_content,
    ):
        mock_broker.publish.side_effect = FastStreamException("connection failed")

        with pytest.raises(FastStreamException):
            await broker_notify_service.send(email_payload_no_content)

        mock_broker.publish.assert_awaited_once()
