from faststream.redis import RedisBroker

from core.utils import get_error_cause
from schemas.notify_schema import (
    DLQMessageSchema,
    EmailNotificationSchema,
    TelegramNotificationSchema,
)

NotificationSchema = EmailNotificationSchema | TelegramNotificationSchema


class DLQService:
    def __init__(self, broker: RedisBroker):
        self._broker = broker

    async def publish_to_dlq(
        self,
        data: NotificationSchema,
        ecx: Exception,
        stream_name: str,
    ) -> None:
        await self._broker.publish(
            DLQMessageSchema(
                original_data=data.model_dump(),
                source_stream=stream_name,
                error=str(ecx),
                error_cause=get_error_cause(ecx),
            ),
            stream=f"{stream_name}.dlq",
        )
