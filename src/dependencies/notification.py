from collections.abc import AsyncGenerator

from infrastructure import broker, db_helper, redis_client
from services.broker_notify_service import BrokerNotifyService
from services.factory import create_notification_service
from services.file_work_service import FileWorkService
from services.notification_dispatcher_service import NotificationDispatcherService


async def get_notify_service() -> AsyncGenerator[BrokerNotifyService, None]:
    yield BrokerNotifyService(broker=broker)


async def get_file_work_service() -> AsyncGenerator[FileWorkService, None]:
    yield FileWorkService(redis=redis_client)


async def get_notification_dispatcher_service() -> AsyncGenerator[
    NotificationDispatcherService, None
]:
    async with db_helper.get_session() as session:
        notification_service = create_notification_service(
            session=session,
        )

        yield NotificationDispatcherService(
            notify_service=notification_service,
            b_service=BrokerNotifyService(
                broker=broker,
            ),
        )
