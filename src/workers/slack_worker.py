import logging
import os
import socket

from faststream import FastStream
from faststream.redis import StreamSub

from core import settings
from core.exceptions import RetryException
from core.utils import get_error_cause
from infrastructure import create_redis_broker
from schemas.notify_schema import SlackNotificationSchema
from services.dlq_service import DLQService
from services.factory import create_slack_notify_service

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


@broker.subscriber(
    stream=StreamSub(
        stream=STREAM_NAME,
        group=GROUP_NAME,
        consumer=CONSUMER_NAME,
        max_records=10,
        polling_interval=1000,
    ),
)
async def slack_worker(data: SlackNotificationSchema) -> None:
    try:
        await service.send(data)

    except RetryException as exc:
        logger.error(
            "Slack delivery failed after retries: channl_id=%s cause=%s",
            data.channel_id,
            get_error_cause(exc),
            exc_info=True,
        )

        try:
            await dlq_service.publish_to_dlq(
                data=data, ecx=exc, stream_name=STREAM_NAME
            )
        except Exception:
            logger.exception("Failed to publish to DLQ: channl_id=%s", data.channel_id)
            raise

    except Exception:
        logger.exception("Unexpected slack worker error: channl_id=%s", data.channel_id)
        raise
