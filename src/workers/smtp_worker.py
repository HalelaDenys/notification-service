import logging
import os
import socket

from faststream import FastStream
from faststream.redis import StreamSub

from core import get_error_cause, settings
from core.exceptions import RetryException, SMTPClientException
from infrastructure import create_redis_broker, db_helper
from schemas.notify_schema import (
    SendEmailMessageToBrokerSchema,
)
from services.dlq_service import DLQService
from services.factory import (
    create_notification_delivery_service,
    create_smtp_notify_service,
)

logging.basicConfig(
    level=settings.logging.log_level_value,
    format=settings.logging.log_format,
)

logger = logging.getLogger(__name__)

STREAM_NAME = "notifications.smtp"
GROUP_NAME = "smtp-workers"
CONSUMER_NAME = f"smtp-{socket.gethostname()}-{os.getpid()}"

broker = create_redis_broker()
app = FastStream(broker)

service = create_smtp_notify_service()
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
async def smtp_worker(notification_data: SendEmailMessageToBrokerSchema) -> None:
    """
    Handle an SMTP notification from the broker.

    :param notification_data: Data required to send the email.
    :return: None
    """

    try:
        deliver_service = create_notification_delivery_service(
            exceptions=(SMTPClientException,),
            db_helper=db_helper,
        )

        try:
            await deliver_service.deliver_notification(
                notify_data=notification_data,
                send_func=lambda: service.send(notification_data.notify_data),
            )
        except RetryException as exc:
            logger.error(
                "Email delivery failed after retries: recipient=%s cause=%s",
                notification_data.notify_data.recipient,
                get_error_cause(exc),
                exc_info=True,
            )

            try:
                await dlq_service.publish_to_dlq(
                    data=notification_data, ecx=exc, stream_name=STREAM_NAME
                )
            except Exception:
                logger.exception(
                    "Failed to publish to DLQ: recipient=%s",
                    notification_data.notify_data.recipient,
                )
                raise

    except Exception:
        logger.exception(
            "Unexpected smtp worker error: recipient=%s",
            notification_data.notify_data.recipient,
        )
        raise
