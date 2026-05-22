import logging
import os
import socket

from faststream import FastStream
from faststream.redis import StreamSub

from infrastructure import create_redis_broker
from schemas.notify_schema import EmailNotificationSchema
from services.factory import create_stmp_notify_service

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
    logger.info("Received email for %s", data.recipient)

    await service.send(data)

    logger.info("Email processed for %s", data.recipient)
