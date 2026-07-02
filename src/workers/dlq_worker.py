import logging
import uuid

from faststream import FastStream
from faststream.redis import StreamSub

from core import settings
from infrastructure import create_redis_broker
from schemas.notify_schema import DLQMessageSchema

logging.basicConfig(
    level=settings.logging.log_level_value,
    format=settings.logging.log_format,
)

logger = logging.getLogger(__name__)


broker = create_redis_broker()
app = FastStream(broker)

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
        # TODO alert admin telegram notification

        return


_register_subscribers()
