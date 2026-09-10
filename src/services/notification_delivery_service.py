from collections.abc import Awaitable, Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core import RetryPolicy, get_error_cause
from infrastructure import DBHelper
from schemas.dtos import CreateNotificationAttemptDTO
from schemas.notify_enums import StatusActionEnum
from schemas.notify_schema import SendMessageToBrokerSchemaType
from services.notification_attempt_service import NotificationAttemptService
from services.notification_service import NotificationService


class NotificationDeliveryService:
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
    ):
        self._notification_service_factory = notification_service_factory
        self._attempt_service_factory = attempt_service_factory
        self._retry_policy = retry_policy
        self._db_helper = db_helper

    async def deliver_notification(
        self,
        notify_data: type[SendMessageToBrokerSchemaType],
        send_func: Callable[[], Awaitable[str | None]],
    ) -> None:
        """
        Deliver a notification using the provided send function with retries.

        :param notify_data: Data required to send the notification.
        :param send_func: Asynchronous callable responsible for sending
            the notification.
        :return: None
        """

        async with self._db_helper.get_session() as session:
            n_service = self._notification_service_factory(
                session,
            )
            await n_service.set_status_processing(notify_data.notify_id)

        await self._retry_policy.execute(
            send_func,
            on_attempt=lambda attempt, started_at, finished_at, response, error: (
                self.handle_attempt(
                    notify_id=notify_data.notify_id,
                    request_payload=notify_data.model_dump(mode="json"),
                    attempt=attempt,
                    started_at=started_at,
                    finished_at=finished_at,
                    response=response,
                    error=error,
                )
            ),
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
        error: Exception | None,
    ) -> None:
        """
        Handle the result of a notification delivery attempt.

        :param notify_id: Notification identifier.
        :param request_payload: Data required to send the notification.
        :param attempt: Attempt number.
        :param started_at: Start time of the delivery attempt.
        :param finished_at: End time of the delivery attempt.
        :param response: Response received from the messaging service provider.
        :param error: Exception raised during the delivery attempt, if any.
        :return: None
        """
        async with self._db_helper.get_session() as session:
            n_service = self._notification_service_factory(
                session,
            )
            attempt_service = self._attempt_service_factory(
                session,
            )

            if error is None:
                if attempt == 1:
                    await n_service.set_status_sent(
                        notify_id=notify_id,
                        provider_message_id=response,
                        last_attempt_at=finished_at,
                    )
                    return

                await self._handle_success_attempt(
                    payload=CreateNotificationAttemptDTO(
                        notify_id=notify_id,
                        request_payload=request_payload,
                        attempt=attempt,
                        started_at=started_at,
                        finished_at=finished_at,
                        provider_message_id=response,
                        status=StatusActionEnum.SUCCESS.value,
                    ),
                    n_service=n_service,
                    attempt_service=attempt_service,
                )
                return

            await self._handle_failure_attempt(
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
                n_service=n_service,
                attempt_service=attempt_service,
            )

    @staticmethod
    async def _handle_success_attempt(
        payload: CreateNotificationAttemptDTO,
        n_service: NotificationService,
        attempt_service: NotificationAttemptService,
    ) -> None:
        """
        Handle a successful notification delivery attempt.

        :param payload: Data containing the notification attempt details.
        :param n_service: Service responsible for notification operations.
        :param attempt_service: Service responsible for notification attempt operations.
        :return: None
        """
        await n_service.set_status_sent(
            notify_id=payload.notify_id,
            provider_message_id=payload.provider_message_id,
            last_attempt_at=payload.finished_at,
        )

        await attempt_service.create_attempt(payload=payload)

    @staticmethod
    async def _handle_failure_attempt(
        payload: CreateNotificationAttemptDTO,
        n_service: NotificationService,
        attempt_service: NotificationAttemptService,
    ):
        """
        Handle a failed notification delivery attempt.

        :param payload: Data containing the notification attempt details.
        :param n_service: Service responsible for notification operations.
        :param attempt_service: Service responsible for notification attempt operations.
        :return: None
        """
        await n_service.set_status_failed(
            notify_id=payload.notify_id,
            error_message=payload.error_message,
            last_attempt_at=payload.finished_at,
        )

        await attempt_service.create_attempt(
            payload=payload,
        )
