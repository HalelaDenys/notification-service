import logging
import os
import socket

from faststream import FastStream
from faststream.redis import StreamSub

from core import settings
from core.exceptions import RetryException
from core.utils import get_error_cause
from infrastructure import create_redis_broker, redis_client
from schemas.notify_schema import TelegramNotificationSchema
from services.dlq_service import DLQService
from services.factory import create_telegram_notify_service

logging.basicConfig(
    level=settings.logging.log_level_value,
    format=settings.logging.log_format,
)

logger = logging.getLogger(__name__)

STREAM_NAME = "notifications.telegram"
GROUP_NAME = "tg-workers"
CONSUMER_NAME = f"tg-{socket.gethostname()}-{os.getpid()}"

broker = create_redis_broker()
app = FastStream(broker)

service = create_telegram_notify_service()
dlq_service = DLQService(broker=broker)


@app.on_startup
async def startup():
    await redis_client.connect()


@app.on_shutdown
async def shutdown():
    await redis_client.disconnect()


@broker.subscriber(
    stream=StreamSub(
        stream=STREAM_NAME,
        group=GROUP_NAME,
        consumer=CONSUMER_NAME,
        max_records=10,
        polling_interval=1000,
    ),
)
async def tg_worker(data: TelegramNotificationSchema) -> None:
    try:
        await service.send(data)

    except RetryException as exc:
        logger.error(
            "Telegram delivery failed after retries: chat_id=%s cause=%s",
            data.chat_id,
            get_error_cause(exc),
            exc_info=True,
        )

        try:
            await dlq_service.publish_to_dlq(
                data=data, ecx=exc, stream_name=STREAM_NAME
            )
        except Exception:
            logger.exception("Failed to publish to DLQ: chat_id=%s", data.chat_id)
            raise

    except Exception:
        logger.exception("Unexpected telegram worker error: chat_id=%s", data.chat_id)
        raise
