from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Notification
from repositories.sqlalchemy_repo import BaseSQLAlchemyRepository
from schemas.notify_enums import StatusEnum

STALE_PROCESSING_TIMEOUT = timedelta(minutes=5)


class NotificationRepository(BaseSQLAlchemyRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Notification, session)

    async def create_idempotency(
        self,
        data: dict,
    ) -> Notification | None:
        """
        Create an alert whilst preventing duplicate records from being created.
        If a field with that idempotency_key already exists,
        simply skip it (ON CONFLICT DO NOTHING).

        :param data: Data required to create the notification.
        :return: Created notification or None if a notification
        with the same idempotency key already exists.
        """

        stmt = (
            insert(self._model)
            .values(**data)
            .on_conflict_do_nothing(
                index_elements=["idempotency_key"],
            )
            .returning(self._model)
        )

        result = await self._session.execute(stmt)

        return result.scalar_one_or_none()

    async def bulk_create_idempotency(
        self, rows: Sequence[dict], batch_size: int = 1000
    ) -> int:
        """
        Bulk insertion for mailings. If a field with this
        idempotency_key already exists, simply skip it (ON CONFLICT DO NOTHING).

        We split the rows into chunks of `batch_size` when inserting them,
        in order to get round PostgreSQL’s limit on the number of join
        parameters in a single query.

        :param rows: A sequence of dict-type values.
        :param batch_size: Number of rows to insert into the database.
        :return: number of insertions.
        """
        if not rows:
            return 0

        total_inserted = 0

        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            stmt = (
                insert(self._model)
                .values(chunk)
                .on_conflict_do_nothing(index_elements=["idempotency_key"])
            )

            result = await self._session.execute(stmt)
            total_inserted += int(result.rowcount or 0)

        return total_inserted

    async def claim(self, notify_id: UUID) -> Notification | None:
        """
        Atomically claim a notification for processing.

        A notification can be claimed if it is in PENDING or QUEUED state,
        or if it is in PROCESSING state but the last attempt is stale.

        :param notify_id: Unique ID of the notification to claim.
        :return: Claimed notification or None if it cannot be claimed.
        """

        stale_before = datetime.now(UTC) - STALE_PROCESSING_TIMEOUT

        stmt = (
            update(self._model)
            .where(
                self._model.id == notify_id,
                or_(
                    self._model.status.in_(
                        [StatusEnum.PENDING.value, StatusEnum.QUEUED.value],
                    ),
                    (self._model.status == StatusEnum.PROCESSING)
                    & (self._model.last_attempt_at < stale_before),
                ),
            )
            .values(status=StatusEnum.PROCESSING)
            .returning(self._model)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_pending_for_relay(self, limit: int = 500) -> list[Notification]:
        """
        Retrieve pending notifications ready for relay and lock them
        to prevent other workers from processing the same records.

        A notification is eligible when:
        - its status is ``pending``;
        - ``next_retry_at`` is NULL or less than/equal to the current time.

        Selected rows are locked using ``FOR UPDATE SKIP LOCKED``,
        allowing multiple workers to process notifications concurrently
        without waiting for rows locked by another worker.

        :param limit: Maximum number of notifications to return.
        :return: list of pending notifications.
        """
        stmt = (
            select(self._model)
            .where(
                self._model.status == StatusEnum.PENDING,
                or_(
                    self._model.next_retry_at.is_(None),
                    self._model.next_retry_at <= func.now(),
                ),
            )
            .order_by(self._model.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_queued(self, ids: Sequence[UUID]) -> None:
        """
        Mark notifications as queued for processing.
        :param ids: the sequence of identifiers that need to be updated
        :return: None
        """
        if not ids:
            return
        await self._session.execute(
            update(self._model)
            .where(self._model.id.in_(ids))
            .values(status=StatusEnum.QUEUED)
        )

    async def count_by_status(self, batch_id: str | UUID) -> dict[str, int]:
        """
        Count notifications grouped by status for a batch.

        :param batch_id: Unique ID of the batch.
        :return: Mapping of notification status to its count.
        """
        stmt = (
            select(self._model.status, func.count())
            .where(self._model.batch_id == batch_id)
            .group_by(self._model.status)
        )
        result = await self._session.execute(stmt)
        return {status.value: count for status, count in result.all()}

    async def cancel_batch(self, batch_id: str | UUID) -> int:
        """
        Cancel all pending and queued notifications in a batch.

        :param batch_id: Unique ID of the batch.
        :return: Number of cancelled notifications.
        """
        result = await self._session.execute(
            update(self._model)
            .where(
                self._model.batch_id == batch_id,
                self._model.status.in_([StatusEnum.PENDING, StatusEnum.QUEUED]),
            )
            .values(status=StatusEnum.CANCELLED)
        )
        return int(result.rowcount or 0)
