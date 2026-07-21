from collections.abc import AsyncGenerator

from infrastructure import broker, redis_client
from services.broker_notify_service import BrokerNotifyService
from services.file_work_service import FileWorkService


async def get_notify_service() -> AsyncGenerator[BrokerNotifyService, None]:
    yield BrokerNotifyService(broker=broker)


async def get_file_work_service() -> AsyncGenerator[FileWorkService, None]:
    yield FileWorkService(redis=redis_client)
