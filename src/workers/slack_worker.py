import logging
import os
import socket

from faststream import FastStream
from faststream.redis import StreamSub

from core import settings
from core.exceptions import RetryException, SlackException
from core.utils import get_error_cause
from infrastructure import create_redis_broker, db_helper, redis_client
from schemas.notify_schema import SendSlackMessageToBrokerSchema
from services.dlq_service import DLQService
from services.factory import (
    create_notification_delivery_service,
    create_slack_notify_service,
)

logging.basicConfig(
    level=settings.logging.log_level_value,
    format=settings.logging.log_format,
)

logger = logging.getLogger(__name__)

STREAM_NAME = "notifications.slack"
GROUP_NAME = "slack-workers"
CONSUMER_NAME = f"slack-{socket.gethostname()}-{os.getpid()}"

broker = create_redis_broker()
app = FastStream(broker)

service = create_slack_notify_service()
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
async def slack_worker(notification_data: SendSlackMessageToBrokerSchema) -> None:
    """
    Processing a notification from a broker on Slack.

    :param notification_data: Data required to send the slack.
    :return: None
    """

    try:
        deliver_service = create_notification_delivery_service(
            exceptions=(SlackException,),
            db_helper=db_helper,
        )
        try:
            await deliver_service.deliver_notification(
                notify_data=notification_data,
                send_func=lambda: service.send(
                    notification_data=notification_data.notify_data
                ),
            )

        except RetryException as exc:
            logger.error(
                "Slack delivery failed after retries: channl_id=%s cause=%s",
                notification_data.notify_data.channel_id,
                get_error_cause(exc),
                exc_info=True,
            )

            try:
                await dlq_service.publish_to_dlq(
                    data=notification_data, ecx=exc, stream_name=STREAM_NAME
                )
            except Exception:
                logger.exception(
                    "Failed to publish to DLQ: channl_id=%s",
                    notification_data.notify_data.channel_id,
                )
                raise

    except Exception:
        logger.exception(
            "Unexpected slack worker error: channl_id=%s",
            notification_data.notify_data.channel_id,
        )
        raise
