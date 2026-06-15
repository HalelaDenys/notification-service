from typing import Protocol, TypeVar

NotificationPayloadT = TypeVar("NotificationPayloadT", contravariant=True)


class NotificationSender(Protocol[NotificationPayloadT]):
    async def send(self, data: NotificationPayloadT) -> None: ...
