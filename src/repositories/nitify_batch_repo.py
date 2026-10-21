from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import NotificationBatch
from repositories.sqlalchemy_repo import BaseSQLAlchemyRepository


class NotificationBatchRepository(BaseSQLAlchemyRepository[NotificationBatch]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NotificationBatch, session)

    async def create_idempotency(
        self,
        data: dict,
    ) -> NotificationBatch | None:
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
