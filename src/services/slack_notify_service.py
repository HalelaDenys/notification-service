import logging

from core import RetryPolicy, settings
from core.exceptions import SlackErrorChannelException
from infrastructure.slack.client import SlackClient
from schemas.notify_schema import SlackNotificationSchema
from services.file_work_service import FileWorkService

logger = logging.getLogger(__name__)


class SlackNotifyService:
    def __init__(
        self,
        client: SlackClient,
        retry_policy: RetryPolicy,
        file_service: FileWorkService,
    ):
        self._client = client
        self._retry_policy = retry_policy
        self._file_service = file_service

    async def send(
        self,
        notify_data: SlackNotificationSchema,
    ) -> None:
        if notify_data.file_id is not None:
            content, meta = await self._file_service.get_file(notify_data.file_id)
            await self.send_file(
                channel_id=notify_data.channel_id,
                text=notify_data.message,
                file_name=meta["file_name"],
                content=content,
                file_size=meta["size"],
            )
        else:
            await self.send_message(
                channel_id=notify_data.channel_id, text=notify_data.message
            )

    async def send_message(self, channel_id: str, text: str) -> None:
        await self._retry_policy.execute(
            self._client.send_message,
            channel_id=channel_id,
            text=text,
        )

    async def send_file(
        self,
        channel_id: str,
        text: str,
        file_name: str,
        content: bytes,
        file_size: int,
    ) -> None:
        await self._retry_policy.execute(
            self._client.send_document,
            channel_id=channel_id,
            text=text,
            file_name=file_name,
            content=content,
            file_size=file_size,
        )

    async def send_error_message_to_channel(
        self,
        error_message: str,
    ) -> None:
        if settings.slack.error_channel_id is None:
            raise SlackErrorChannelException("ERROR_CHANNEL_ID is not configured.")

        await self._retry_policy.execute(
            self._client.send_message,
            channel_id=settings.slack.error_channel_id,
            text=error_message,
        )
