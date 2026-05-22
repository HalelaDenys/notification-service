import logging

from faststream.exceptions import FastStreamException

from schemas.notify_schema import NotificationRequestSchema

logger = logging.getLogger(__name__)


class BrokerNotifyService:
    def __init__(self, broker):
        self.broker = broker

    async def send(self, data: NotificationRequestSchema) -> None:
        try:
            await self.broker.publish(
                data,
                stream=f"notifications.{data.type}",
            )
        except FastStreamException as exc:
            logger.error("Failed to publish lead to Redis Stream: %s", exc)
            raise
