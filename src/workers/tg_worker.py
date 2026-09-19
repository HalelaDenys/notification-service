import logging
import os
import socket

from faststream import FastStream
from faststream.redis import StreamSub

from core import settings
from core.exceptions import RetryException, TelegramException
from core.utils import get_error_cause
from infrastructure import create_redis_broker, db_helper, redis_client
from schemas.notify_schema import SendTelegramMessageToBrokerSchema
from services.dlq_service import DLQService
from services.factory import (
    create_notification_delivery_service,
    create_telegram_notify_service,
)

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
async def tg_worker(notification_data: SendTelegramMessageToBrokerSchema) -> None:
    """
    Processing a notification from a broker on Telegram.

    :param notification_data: Data required to send the telegram.
    :return: None
    """
    try:
        deliver_service = create_notification_delivery_service(
            exceptions=(TelegramException,),
            db_helper=db_helper,
        )

        try:
            await deliver_service.deliver_notification(
                notify_data=notification_data,
                send_func=lambda: service.send(notification_data.notify_data),
            )
        except RetryException as exc:
            logger.error(
                "Telegram delivery failed after retries: chat_id=%s cause=%s",
                notification_data.notify_data.chat_id,
                get_error_cause(exc),
                exc_info=True,
            )

            try:
                await dlq_service.publish_to_dlq(
                    data=notification_data, ecx=exc, stream_name=STREAM_NAME
                )
            except Exception:
                logger.exception(
                    "Failed to publish to DLQ: chat_id=%s",
                    notification_data.notify_data.chat_id,
                )
                raise
    except Exception:
        logger.exception(
            "Unexpected telegram worker error: chat_id=%s",
            notification_data.notify_data.chat_id,
        )
        raise
