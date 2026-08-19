from infrastructure.db.models import Notification
from repositories.notify_repo import NotificationRepository


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
