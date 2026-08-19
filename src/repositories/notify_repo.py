from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Notification
from repositories.sqlalchemy_repo import BaseSQLAlchemyRepository


class NotificationRepository(BaseSQLAlchemyRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Notification, session)

    async def create_idempotency(
        self,
        data: dict,
    ) -> Notification | None:
        """
        :param data: created data
        :return: Model instance or None
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
