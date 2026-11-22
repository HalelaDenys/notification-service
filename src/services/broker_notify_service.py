import logging

from faststream.exceptions import FastStreamException
from faststream.redis import RedisBroker
from redis import RedisError

from infrastructure import RedisClient
from schemas.notify_schema import (
    BatchNotificationRequestSchema,
    EmailNotificationSchema,
    SendEmailMessageToBrokerSchema,
    SendMessageToBrokerSchemaType,
    SendSlackMessageToBrokerSchema,
    SendTelegramMessageToBrokerSchema,
    SlackNotificationSchema,
    TelegramNotificationSchema,
)

logger = logging.getLogger(__name__)


class BrokerNotifyService:
    def __init__(
        self,
        broker: RedisBroker,
        redis_client: RedisClient | None = None,
    ) -> None:
        self._broker = broker
        if redis_client is not None:
            self._redis = redis_client.client

    async def send(self, data: SendMessageToBrokerSchemaType) -> None:
        try:
            await self._broker.publish(
                data,
                stream=f"notifications.{data.notify_data.type}",
            )
        except FastStreamException as exc:
            logger.error("Failed to publish lead to Redis Stream: %s", exc)
            raise

    async def batch_publish(
        self,
        data: BatchNotificationRequestSchema,
        notify_id: int,
        size_chunk: int = 500,
    ) -> int:
        """
        Publishes messages to the queue (Redis streams) in batches.

        Splits the list of recipients into chunks of size_chunk,
        creates a separate message for each recipient, and
        publishes the messages to the Redis stream using a pipeline.

        :param data: Notification data and list of recipients.
        :param notify_id: Notification ID.
        :param size_chunk: Number of messages in a single batch.
        :return: Number of messages published.
        """
        if self._redis is None:
            raise RuntimeError("Redis client is not set")
        recipients = data.recipients

        if not recipients:
            return 0

        if size_chunk <= 0:
            raise ValueError("size_chunk must be greater than zero")

        published = 0
        stream = f"notifications.{data.type}"

        for i in range(0, len(recipients), size_chunk):
            chunk = recipients[i : i + size_chunk]

            try:
                async with self._redis.pipeline(transaction=False) as pipe:
                    for recipient in chunk:
                        message = self._create_message(
                            data=data,
                            notify_id=notify_id,
                            recipient_data=recipient.model_dump(),
                        )

                        await self._broker.publish(
                            message,
                            stream=stream,
                            pipeline=pipe,
                        )
                    await pipe.execute()
            except (FastStreamException, RedisError):
                logger.exception(
                    "Failed to publish notification batch. "
                    "Notify ID: %s, chunk offset: %s, chunk size: %s",
                    notify_id,
                    i,
                    len(chunk),
                )
                raise

            published += len(chunk)

        return published

    def _create_message(
        self,
        data: BatchNotificationRequestSchema,
        notify_id: int,
        recipient_data: dict,
    ):
        """
        Generates a message based on the received schema.

        :param data: Notification data and list of recipients.
        :param notify_id: Notification ID.
        :param recipient_data: Recipient data.
        """

        schema = self._determine_broker_schema(data.type)

        if isinstance(schema, type(SendEmailMessageToBrokerSchema)):
            return SendEmailMessageToBrokerSchema(
                notify_id=notify_id,
                notify_data=EmailNotificationSchema(
                    type=data.type,
                    message=data.message,
                    recipient=recipient_data["recipient"],
                    subject=recipient_data["subject"],
                    context=recipient_data.get("context"),
                ),
            ).model_dump(mode="json")
        elif isinstance(schema, type(SendTelegramMessageToBrokerSchema)):
            return SendTelegramMessageToBrokerSchema(
                notify_id=notify_id,
                notify_data=TelegramNotificationSchema(
                    type=data.type,
                    message=data.message,
                    chat_id=recipient_data["chat_id"],
                    reply_markup=recipient_data.get("reply_markup"),
                    file_id=recipient_data.get("file_id"),
                ),
            ).model_dump(mode="json")
        elif isinstance(schema, type(SendSlackMessageToBrokerSchema)):
            return SendSlackMessageToBrokerSchema(
                notify_id=notify_id,
                notify_data=SlackNotificationSchema(
                    type=data.type,
                    message=data.message,
                    channel_id=recipient_data["channel_id"],
                    file_id=recipient_data.get("file_id"),
                ),
            ).model_dump(mode="json")
        return None

    @staticmethod
    def _determine_broker_schema(
        stream_type: str,
    ) -> (
        SendSlackMessageToBrokerSchema
        | SendTelegramMessageToBrokerSchema
        | SendEmailMessageToBrokerSchema
    ):
        """
        Determines the message schema based on the message type.

        :param stream_type: notification type.
        :return: type schema.
        """
        match stream_type:
            case "smtp":
                return SendEmailMessageToBrokerSchema
            case "telegram":
                return SendTelegramMessageToBrokerSchema
            case "slack":
                return SendSlackMessageToBrokerSchema
        return None
