import logging
import uuid

from faststream import FastStream
from faststream.redis import StreamSub

from core import settings
from core.exceptions import ApplicationException
from infrastructure import create_redis_broker
from schemas.notify_schema import DLQMessageSchema
from services.factory import create_telegram_notify_service

logging.basicConfig(
    level=settings.logging.log_level_value,
    format=settings.logging.log_format,
)

logger = logging.getLogger(__name__)


broker = create_redis_broker()
app = FastStream(broker)
tg_service = create_telegram_notify_service()

DLQ_STREAMS = [
    "notifications.telegram.dlq",
    "notifications.smtp.dlq",
]


def _register_subscribers():
    for stream_name in DLQ_STREAMS:
        _make_subscriber(stream_name)


def _make_subscriber(stream_name: str) -> StreamSub:
    @broker.subscriber(
        stream=StreamSub(
            stream=stream_name,
            group="dlq-alerters",
            consumer=f"dlq-alerters-{stream_name}-{uuid.uuid4()}",
            polling_interval=3000,
        )
    )
    async def dlq_handler(msg: DLQMessageSchema) -> None:
        logger.error(
            "DLQ message received from %s: source=%s error=%s cause=%s failed_at=%s",
            stream_name,
            msg.source_stream,
            msg.error,
            msg.error_cause,
            msg.failed_at,
        )
        # TODO alert sentry
        # TODO alert slack
        if settings.tg.admin_notify:
            try:
                await tg_service.send_admin_error_message(
                    error_message=(
                        f"🚨 DLQ message received\n"
                        f"Stream: {stream_name}\n"
                        f"Source: {msg.source_stream}\n"
                        f"Error: {msg.error}\n"
                        f"Cause: {msg.error_cause}\n"
                        f"Failed at: {msg.failed_at}"
                    )
                )
            except ApplicationException:
                logger.exception(
                    "Failed to send Telegram alert. Source stream: %s",
                    msg.source_stream,
                )


_register_subscribers()
