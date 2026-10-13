from datetime import datetime
from uuid import UUID

from core.exceptions import NotificationNotFoundError
from infrastructure.db.models import Notification
from repositories.notify_repo import NotificationRepository
from schemas.notify_enums import StatusEnum


class NotificationService:
    def __init__(
        self,
        notify_repo: NotificationRepository,
    ) -> None:
        self._notify_repo = notify_repo

    async def save_notification(
        self,
        payload: dict,
    ) -> Notification | None:
        """
        Save notification to database.
        :param payload: Payload of the notification.
        :return: Notification or None if it cannot be saved.
        """
        return await self._notify_repo.create_idempotency(payload)

    async def claim(self, notify_id: UUID) -> Notification | None:
        """
        Atomically claim a notification for processing.
        Returns None if it's already sent/cancelled/claimed elsewhere —
        caller (worker) should just ack the broker message and skip.

        :param notify_id: Unique ID of the notification to claim.
        :return: Claimed notification or None if it cannot be claimed.
        """
        return await self._notify_repo.claim(notify_id)

    async def set_status_processing(self, notify_id: UUID) -> Notification:
        """
        Sets the status to PROCESSING for the specified notify_id.

        :param notify_id: Unique ID of the notification to set.
        :return: Notification object or error(NotificationNotFoundError)
        if it cannot be set.
        """
        notification = await self.update_notification(
            data={"status": StatusEnum.PROCESSING.value}, notify_id=notify_id
        )

        if notification is None:
            raise NotificationNotFoundError(
                f"Notification {notify_id} not found",
            )
        return notification

    async def set_status_failed(
        self,
        notify_id: UUID,
        *,
        error_message: str | None = None,
        last_attempt_at: datetime | None = None,
    ) -> Notification:
        """
        Final state: non-retryable error. No more attempts will happen.

        :param notify_id:  Unique ID of the notification to set.
        :param error_message: Error message for the notification
        :param last_attempt_at: The time of the last attempt
        :return: Notification object or error(NotificationNotFoundError)
        if it cannot be set
        """
        notification = await self.get_notification(notify_id)

        if notification is None:
            raise NotificationNotFoundError(
                f"Notification {notify_id} not found",
            )

        updated = await self.update_notification(
            notify_id=notify_id,
            data={
                "status": StatusEnum.FAILED.value,
                "retry_count": notification.retry_count + 1,
                "last_attempt_at": last_attempt_at,
                "next_retry_at": None,
                "error_message": error_message,
            },
        )

        if updated is None:
            raise NotificationNotFoundError(
                f"Notification {notify_id} not found",
            )
        return updated

    async def set_status_sent(
        self,
        notify_id: UUID,
        *,
        provider_message_id: str | None = None,
        last_attempt_at: datetime | None = None,
    ) -> Notification:
        """
        Sets the status to SENT for the specified notify_id.

        :param notify_id: unique ID of the notification to set.
        :param provider_message_id: Message ID from the provider
        :param last_attempt_at: The time of the last attempt
        :return: Notification object or error(NotificationNotFoundError)
        if it cannot be se
        """
        notification = await self.update_notification(
            notify_id=notify_id,
            data={
                "status": StatusEnum.SENT.value,
                "provider_message_id": provider_message_id,
                "last_attempt_at": last_attempt_at,
                "error_message": None,
                "next_retry_at": None,
            },
        )
        if notification is None:
            raise NotificationNotFoundError(
                f"Notification {notify_id} not found",
            )
        return notification

    async def get_status_dlq(
        self,
        notify_id: UUID,
        *,
        error_message: str | None = None,
        last_attempt_at: datetime | None = None,
    ) -> Notification | None:
        """
        Final state: retries exhausted for a retryable error.

        :param notify_id:  Unique ID of the notification to set.
        :param error_message: Error message for the notification
        :param last_attempt_at: The time of the last attempt
        :return: Notification object or error(NotificationNotFoundError)
        if it cannot be set
        """
        notification = await self.get_notification(notify_id=notify_id)

        if notification is None:
            raise NotificationNotFoundError(
                f"Notification {notify_id} not found",
            )

        updated = await self.update_notification(
            notify_id=notify_id,
            data={
                "status": StatusEnum.DLQ.value,
                "retry_count": notification.retry_count + 1,
                "last_attempt_at": last_attempt_at,
                "next_retry_at": None,
                "error_message": error_message,
            },
        )

        if updated is None:
            raise NotificationNotFoundError(
                f"Notification {notify_id} not found",
            )
        return updated

    async def schedule_retry(self, notify_id: UUID, *, error_massae) -> Notification:
        pass

    async def bulk_save_notifications(self, rows: list[dict]) -> int:
        """
        Stores a list of notifications in the database.

        Records with duplicate ``idempotency_key`` values are ignored.

        :param rows: A list of data to be inserted.
        :return: The number of records actually inserted.
        """
        return await self._notify_repo.bulk_create_idempotency(rows=rows)

    async def get_batch_progress(self, batch_id: str | UUID) -> dict[str, int]:
        """
        Returns the number of notifications in a batch, grouped by status.

        :param batch_id: The unique batch identifier.
        :return: The number of notifications for each status.
        """
        return await self._notify_repo.count_by_status(batch_id=batch_id)

    async def canceled_batch_notifications(self, batch_id: str | UUID) -> int:
        """
        Cancels all batch notifications that can still be cancelled.

        :param batch_id: The unique batch identifier.
        :return: The number of notifications cancelled.
        """
        return await self._notify_repo.cancel_batch(batch_id=batch_id)

    async def get_notification(self, notify_id: UUID) -> Notification | None:
        return await self._notify_repo.find_one(id=notify_id)

    async def update_notification(
        self, notify_id: UUID, data: dict
    ) -> Notification | None:
        return await self._notify_repo.update(data=data, id=notify_id)
