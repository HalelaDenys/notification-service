from faststream.redis import RedisBroker

from core.utils import get_error_cause
from schemas.notify_schema import (
    DLQSchema,
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
            DLQSchema(
                recipient=self._get_recipient(data),
                source_stream=stream_name,
                error_type=type(ecx).__name__,
                error=str(ecx),
                error_cause=get_error_cause(ecx),
                payload=data,
            ),
            stream=f"{stream_name}.dlq",
        )

    def _get_recipient(self, data: NotificationSchema) -> str:
        if isinstance(data, EmailNotificationSchema):
            return str(data.recipient)

        return str(data.chat_id)
