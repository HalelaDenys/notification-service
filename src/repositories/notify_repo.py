from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import Notification
from repositories.sqlalchemy_repo import BaseSQLAlchemyRepository


class NotificationRepository(BaseSQLAlchemyRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Notification, session)
