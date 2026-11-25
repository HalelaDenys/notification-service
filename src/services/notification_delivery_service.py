import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core import RetryPolicy, get_error_cause
from core.exceptions import NonRetryableError, RetryableError
from infrastructure import DBHelper
from schemas.dtos import CreateNotificationAttemptDTO
from schemas.notify_enums import StatusActionEnum
from schemas.notify_schema import SendMessageToBrokerSchemaType
from services.dlq_service import DLQService
from services.notification_attempt_service import NotificationAttemptService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class NotificationDeliveryService:
    """
    Manage notification delivery attempts, retries, and failure handling.
    """

    def __init__(
        self,
        notification_service_factory: Callable[
            [AsyncSession],
            NotificationService,
        ],
        attempt_service_factory: Callable[
            [AsyncSession],
            NotificationAttemptService,
        ],
        retry_policy: RetryPolicy,
        db_helper: DBHelper,
        dlq_service: DLQService,
        stream_name: str,
    ):
        self._notification_service_factory = notification_service_factory
        self._attempt_service_factory = attempt_service_factory
        self._retry_policy = retry_policy
        self._db_helper = db_helper
        self._dlq_service = dlq_service
        self._stream_name = stream_name

    async def deliver_notification(
        self,
        notify_data: SendMessageToBrokerSchemaType,
        send_func: Callable[[], Awaitable[str | None]],
    ) -> None:
        """
        Claim a notification and execute one delivery attempt.

        The attempt result is passed to `handle_attempt` for persistence
        and further processing.

        :param notify_data: Notification data received from the broker.
        :param send_func: Async callable that sends the notification.
        :return: None.
        """
        async with self._db_helper.get_session() as session:
            n_service = self._notification_service_factory(
                session,
            )
            notification = await n_service.claim(notify_id=notify_data.notify_id)

        if notification is None:
            logger.info(
                "Skipping notify_id=%s, already handled or claimed elsewhere ",
                notify_data.notify_id,
            )
            return

        attempt = notification.retry_count + 1

        result, error, started_at, finished_at = await self._retry_policy.execute_once(
            func=send_func,
        )

        await self.handle_attempt(
            notify_id=notify_data.notify_id,
            request_payload=notify_data.model_dump(mode="json"),
            attempt=attempt,
            started_at=started_at,
            finished_at=finished_at,
            response=result,
            error=error,
            notify_data=notify_data,
        )

    async def handle_attempt(
        self,
        *,
        notify_id: UUID,
        request_payload: dict,
        attempt: int,
        started_at: datetime,
        finished_at: datetime,
        response: str | None,
        error: RetryableError | NonRetryableError | None,
        notify_data: SendMessageToBrokerSchemaType,
    ) -> None:
        """
        Persist and process the result of a notification delivery attempt.

        Successful attempts mark the notification as sent. Retryable errors
        schedule another attempt or move the notification to the DLQ when
        the retry limit is reached. Non-retryable errors mark the
        notification as failed.

        :param notify_id: Identifier of the notification.
        :param request_payload: Serialized notification request.
        :param attempt: Current delivery attempt number.
        :param started_at: Time when the attempt started.
        :param finished_at: Time when the attempt finished.
        :param response: Provider response or message identifier, if available.
        :param error: Error raised during the delivery attempt, if any.
        :param notify_data: Original notification data used for DLQ publishing.
        :return: None.
        """
        async with self._db_helper.get_session() as session:
            n_service = self._notification_service_factory(
                session,
            )
            attempt_service = self._attempt_service_factory(
                session,
            )
            # The Branch of Success
            if error is None:
                await n_service.set_status_sent(
                    notify_id=notify_id,
                    provider_message_id=response,
                    last_attempt_at=finished_at,
                )

                await attempt_service.create_attempt(
                    payload=CreateNotificationAttemptDTO(
                        notify_id=notify_id,
                        request_payload=request_payload,
                        attempt=attempt,
                        started_at=started_at,
                        finished_at=finished_at,
                        provider_message_id=response,
                        status=StatusActionEnum.SUCCESS.value,
                    ),
                )
                return
            # A branch with an error. We always record the attempt
            await attempt_service.create_attempt(
                payload=CreateNotificationAttemptDTO(
                    notify_id=notify_id,
                    request_payload=request_payload,
                    attempt=attempt,
                    started_at=started_at,
                    finished_at=finished_at,
                    provider_message_id=response,
                    status=StatusActionEnum.FAILED.value,
                    error_message=str(error),
                    error_cause=get_error_cause(error),
                ),
            )

            is_retryable = self._retry_policy.is_retryable(error=error)
            attempt_left = self._retry_policy.max_attempts - attempt

            # The error is transient and attempts are still being
            # made -> we set the status back to ‘PENDING’
            if is_retryable and attempt_left > 0:
                next_retry_second = timedelta(
                    seconds=(
                        error.retry_after
                        if error.retry_after is not None
                        else self._retry_policy.next_daley(attempt)
                    )
                )

                await n_service.schedule_retry(
                    notify_id=notify_id,
                    error_massage=str(error),
                    last_attempt_at=finished_at,
                    next_retry_at=finished_at + next_retry_second,
                )
                logger.warning(
                    "Attempt %s/%s failed for notify_id=%s, will retry: %s",
                    attempt,
                    self._retry_policy.max_attempts,
                    notify_id,
                    error,
                )
                return
            # The error is transient, no further attempts will be made + DLQ
            if is_retryable:
                await n_service.set_status_dlq(
                    notify_id=notify_id,
                    error_message=str(error),
                    last_attempt_at=finished_at,
                )
                logger.error(
                    "notify_id=%s, exhausted retries, moving to DLQ: %s",
                    notify_id,
                    f"Type: {type(error).__name__}, "
                    f"cause: {error.cause_type}, "
                    f"code={error.status_code}",
                )
                try:
                    await self._dlq_service.publish_to_dlq(
                        notify_data=notify_data,
                        error=error,
                        stream_name=self._stream_name,
                    )
                except Exception:
                    logger.exception(
                        "Failed to publish to DLQ: notify_id=%s",
                        notify_id,
                    )
                    raise
                return

            # Permanent error -> immediate ‘FAILED’ status, without a retry
            await n_service.set_status_failed(
                notify_id=notify_id,
                error_message=str(error),
                last_attempt_at=finished_at,
            )
            logger.error(
                "notify_id=%s non-retryable failure: %s",
                notify_id,
                get_error_cause(error),
            )
            return
