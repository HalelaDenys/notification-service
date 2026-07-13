import logging

from core import RetryPolicy
from infrastructure.slack.client import SlackClient
from schemas.notify_schema import SlackNotificationSchema

logger = logging.getLogger(__name__)


class SlackNotifyService:
    def __init__(
        self,
        client: SlackClient,
        retry_policy: RetryPolicy,
    ):
        self._client = client
        self._retry_policy = retry_policy

    async def send(
        self, notify_data: SlackNotificationSchema, file_name: str | None = None
    ) -> None:
        if file_name is None:
            await self.send_message(
                channel_id=notify_data.channel_id, text=notify_data.message
            )
        else:
            logger.info("SlackNotifyService sending file")

    async def send_message(self, channel_id: str, text: str):
        await self._retry_policy.execute(
            self._client.send_message,
            channel_id=channel_id,
            text=text,
        )

    async def send_file(self) -> None:
        raise NotImplementedError("Method not implemented")
