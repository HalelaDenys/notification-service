import logging
import os
import socket

from faststream import FastStream
from faststream.redis import StreamSub

from core import settings
from core.exceptions import RetryError
from infrastructure import create_redis_broker
from schemas.notify_schema import DLQSchema, EmailNotificationSchema
from services.factory import create_stmp_notify_service

logging.basicConfig(
    level=settings.logging.log_level_value,
    format=settings.logging.log_format,
)

logger = logging.getLogger(__name__)

STREAM_NAME = "notifications.email"
GROUP_NAME = "smtp-workers"
CONSUMER_NAME = f"smtp-{socket.gethostname()}-{os.getpid()}"

broker = create_redis_broker()

app = FastStream(broker)

service = create_stmp_notify_service()


@broker.subscriber(
    stream=StreamSub(
        stream=STREAM_NAME,
        group=GROUP_NAME,
        consumer=CONSUMER_NAME,
        max_records=10,
        polling_interval=1000,
    ),
)
async def smtp_worker(data: EmailNotificationSchema) -> None:
    try:
        await service.send(data)

    except RetryError as exc:
        logger.error(
            "Email delivery failed after retries: recipient=%s",
            data.recipient,
        )

        try:
            await broker.publish(
                DLQSchema(
                    recipient=data.recipient, error=str(exc), payload=data.model_dump()
                ),
                stream="notifications.email.dlq",
            )
        except Exception:
            logger.exception("Failed to publish to DLQ: recipient=%s", data.recipient)
            raise

    except Exception:
        logger.exception("Unexpected error")
        raise
