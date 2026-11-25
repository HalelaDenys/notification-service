from faststream.redis import RedisBroker

from core.utils import get_error_cause
from schemas.notify_schema import (
    DLQMessageToBrokerSchema,
    NotificationRequestSchema,
)


class DLQService:
    def __init__(self, broker: RedisBroker):
        self._broker = broker

    async def publish_to_dlq(
        self,
        notify_data: NotificationRequestSchema,
        error: Exception,
        stream_name: str,
    ) -> None:
        """
        Publish a failed notification to the dead-letter stream.

        :param notify_data: Original notification request data.
        :param error: Exception that caused the notification delivery to fail.
        :param stream_name: Name of the original notification stream.
        :return: None.
        """
        await self._broker.publish(
            DLQMessageToBrokerSchema(
                original_data=notify_data.model_dump(),
                source_stream=stream_name,
                error_message=str(error),
                error_full_cause=get_error_cause(error),
            ),
            stream=f"{stream_name}.dlq",
        )
