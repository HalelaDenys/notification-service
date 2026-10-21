from typing import Protocol

from schemas.dtos import NotificationDTO


class AsyncClientProtocol(Protocol[NotificationDTO]):
    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def send(self, notification_data: NotificationDTO) -> None: ...
