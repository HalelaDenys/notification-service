import time
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import NotificationBatchNotFoundError
from infrastructure import DBHelper
from infrastructure.db.models import NotificationBatch
from repositories.nitify_batch_repo import NotificationBatchRepository
from schemas.notify_enums import ChannelEnum, StatusEnum
from schemas.notify_schema import (
    BatchCreatedResponseSchema,
    BatchNotificationRequestSchema,
    BatchStatusResponseSchema,
    SlackBatchNotificationRequestSchema,
    SMTPBatchNotificationRequestSchema,
    TelegramBatchNotificationRequestSchema,
)
from services.notification_service import NotificationService


class NotificationBatchService:
    def __init__(
        self,
        batch_repo_factory: Callable[
            [AsyncSession],
            NotificationBatchRepository,
        ],
        notification_service_factory: Callable[
            [AsyncSession],
            NotificationService,
        ],
        db_helper: DBHelper,
    ):
        self._batch_repo_factory = batch_repo_factory
        self._notification_service_factory = notification_service_factory
        self._db_helper = db_helper

    async def create_batch(
        self,
        batch_data: BatchNotificationRequestSchema,
        idempotency_key: str | None,
    ) -> BatchCreatedResponseSchema:
        """
        Create a notification batch and its associated notifications.

        Creates one NotificationBatch record and the corresponding
        Notification records for each recipient.

        :param batch_data: Batch notification request data.
        :param idempotency_key: Optional key used to prevent duplicate batches.
        :return: Created batch information.
        """
        async with self._db_helper.get_session() as session:
            batch_repo = self._batch_repo_factory(session)

            # якщо idempotency_key є, а existing інсує повертаємо існуючий Batch
            if idempotency_key:
                existing = await self._find_existing_idempotency_key(
                    batch_repo, idempotency_key
                )
                if existing is not None:
                    return BatchCreatedResponseSchema(
                        batch_id=existing.id,
                        total=existing.total,
                        skipped_duplicates=0,
                        idempotent_replay=True,
                    )

            batch = await batch_repo.create_idempotency(
                data={
                    "idempotency_key": idempotency_key,
                    "total": len(batch_data.recipients),
                }
            )
            # якщо batch нестворився або він вже існує і existing його знайшов
            # повертаємо існуючий Batch.
            if batch is None:
                existing = await self._find_existing_idempotency_key(
                    batch_repo, idempotency_key
                )
                if existing is not None:
                    return BatchCreatedResponseSchema(
                        batch_id=existing.id,
                        total=existing.total,
                        skipped_duplicates=0,
                        idempotent_replay=True,
                    )
                raise RuntimeError("Failed to create or find notification batch")

            start = time.perf_counter()
            print("start: ", start)
            rows = self._build_notification_rows(batch_data, batch.id)

            n_service = self._notification_service_factory(session)
            inserted = await n_service.bulk_save_notifications(rows)

            end = time.perf_counter()
            print("end: ", end)
            print("full time: ", end - start)
            return BatchCreatedResponseSchema(
                batch_id=batch.id,
                total=inserted,
                skipped_duplicates=len(rows) - inserted,
                idempotent_replay=False,
            )

    async def get_status(self, batch_id: str | UUID) -> BatchStatusResponseSchema:
        """
        Retrieve the status and progress of a notification batch.

        :param batch_id: Unique identifier of the notification batch.
        :return: Notification batch status and delivery statistics.
        """
        async with self._db_helper.get_session() as session:
            batch_repo = self._batch_repo_factory(session)
            batch = await batch_repo.find_one(id=UUID(str(batch_id)))

            if batch is None:
                raise NotificationBatchNotFoundError(f"Batch {batch_id} not found")

            n_service = self._notification_service_factory(session)
            counts = await n_service.get_batch_progress(batch_id=UUID(str(batch_id)))

        return BatchStatusResponseSchema(
            batch_id=batch.id,
            total=batch.total,
            pending=counts.get(StatusEnum.PENDING.value, 0),
            queued=counts.get(StatusEnum.QUEUED.value, 0),
            processing=counts.get(StatusEnum.PROCESSING.value, 0),
            sent=counts.get(StatusEnum.SENT.value, 0),
            failed=counts.get(StatusEnum.FAILED.value, 0),
            dlq=counts.get(StatusEnum.DLQ.value, 0),
            cancelled=counts.get(StatusEnum.CANCELLED.value, 0),
            cancelled_at=batch.cancelled_at.isoformat() if batch.cancelled_at else None,
        )

    async def cancel_batch(self, batch_id: str | UUID) -> BatchStatusResponseSchema:
        """
        Cancel pending notifications in a batch.

        :param batch_id: Unique identifier of the notification batch.
        :return: Updated batch status and delivery statistics.
        """
        async with self._db_helper.get_session() as session:
            batch_repo = self._batch_repo_factory(session)
            batch = await batch_repo.find_one(id=UUID(str(batch_id)))
            if batch is None:
                raise NotificationBatchNotFoundError(f"Batch {batch_id} not found")

            await batch_repo.update(
                data={"cancelled_at": datetime.now(UTC)},
                id=batch.id,
            )

            n_service = self._notification_service_factory(session)
            await n_service.canceled_batch_notifications(batch_id=UUID(str(batch_id)))

            return await self.get_status(batch_id=batch.id)

    @staticmethod
    async def _find_existing_idempotency_key(
        batch_repo: NotificationBatchRepository, idempotency_key: str | UUID
    ) -> NotificationBatch | None:
        """
        Find a notification batch by its idempotency key.

        :param batch_repo: Repository used to access notification batches.
        :param idempotency_key: Idempotency key used to identify the batch.
        :return: Existing notification batch or None if not found.
        """
        return await batch_repo.find_one(idempotency_key=idempotency_key)

    @staticmethod
    def _build_notification_rows(
        batch_data: BatchNotificationRequestSchema, batch_id: str | UUID
    ) -> list[dict]:
        """
        Determine the notification type and build
        rows for bulk database insertion.

        :param batch_data: Batch notification request data.
        :param batch_id: Identifier of the notification batch.
        :return: List of notification rows.
        """
        rows: list[dict] = []

        if isinstance(batch_data, SMTPBatchNotificationRequestSchema):
            for r in batch_data.recipients:
                row = {
                    "batch_id": batch_id,
                    "channel": ChannelEnum.SMTP.value,
                    "message": batch_data.message,
                    "subject": batch_data.subject,
                    "recipient": r.recipient,
                    "status": StatusEnum.PENDING.value,
                    "idempotency_key": f"{batch_id}:{r.recipient}",
                }
                if r.context is not None:
                    row["payload"] = r.context.model_dump(mode="json")
                rows.append(row)
        elif isinstance(batch_data, TelegramBatchNotificationRequestSchema):
            shared_markup = (
                batch_data.reply_markup.model_dump(mode="json")
                if batch_data.reply_markup is not None
                else None
            )
            for r in batch_data.recipients:
                row = {
                    "batch_id": batch_id,
                    "channel": ChannelEnum.TELEGRAM.value,
                    "message": batch_data.message,
                    "chat_id": str(r.chat_id),
                    "status": StatusEnum.PENDING.value,
                    "idempotency_key": f"{batch_id}:{r.chat_id}",
                }
                if shared_markup is not None:
                    row["payload"] = shared_markup
                if r.file_id is not None:
                    row["file_id"] = r.file_id
                rows.append(row)
        elif isinstance(batch_data, SlackBatchNotificationRequestSchema):
            for r in batch_data.recipients:
                row = {
                    "batch_id": batch_id,
                    "channel": ChannelEnum.SLACK.value,
                    "message": batch_data.message,
                    "status": StatusEnum.PENDING.value,
                    "channel_id": str(r.channel_id),
                    "idempotency_key": f"{batch_id}:{r.channel_id}",
                }
                if r.file_id is not None:
                    row["file_id"] = r.file_id
                rows.append(row)

        return rows
