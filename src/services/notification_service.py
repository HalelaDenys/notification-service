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
        return await self._notify_repo.create_idempotency(payload)

    async def set_status_processing(self, notify_id: UUID) -> Notification:
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
        next_retry_at: datetime | None = None,
    ) -> Notification:
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
                "next_retry_at": next_retry_at,
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

    async def get_notification(self, notify_id: UUID) -> Notification | None:
        return await self._notify_repo.find_one(id=notify_id)

    async def update_notification(
        self, notify_id: UUID, data: dict
    ) -> Notification | None:
        return await self._notify_repo.update(data=data, id=notify_id)
