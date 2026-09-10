from infrastructure.db.models import NotificationAttempt
from repositories.notify_attempt_repo import NotificationAttemptRepository
from schemas.dtos import CreateNotificationAttemptDTO


class NotificationAttemptService:
    def __init__(
        self,
        attempt_repo: NotificationAttemptRepository,
    ) -> None:
        self._attempt_repo = attempt_repo

    async def create_attempt(
        self, payload: CreateNotificationAttemptDTO
    ) -> NotificationAttempt:
        return await self._attempt_repo.create(
            {
                "notification_id": payload.notify_id,
                "attempt": payload.attempt,
                "status": payload.status,
                "request_payload": payload.request_payload,
                "response_payload": (
                    {"message_id": payload.provider_message_id}
                    if payload.provider_message_id
                    else None
                ),
                "provider_message_id": payload.provider_message_id,
                "started_at": payload.started_at,
                "finished_at": payload.finished_at,
                "error_message": payload.error_message,
                "error_cause": payload.error_cause,
            }
        )
