from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import NotificationAttempt
from repositories.sqlalchemy_repo import BaseSQLAlchemyRepository


class NotificationAttemptRepository(BaseSQLAlchemyRepository[NotificationAttempt]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(NotificationAttempt, session)
