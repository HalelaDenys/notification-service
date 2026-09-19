import logging

from core import settings
from core.exceptions import SlackErrorChannelException
from infrastructure.slack.client import SlackClient
from schemas.notify_schema import SlackNotificationSchema
from services.file_work_service import FileWorkService

logger = logging.getLogger(__name__)


class SlackNotifyService:
    def __init__(
        self,
        client: SlackClient,
        file_service: FileWorkService,
    ):
        self._client = client
        self._file_service = file_service

    async def send(
        self,
        notification_data: SlackNotificationSchema,
    ) -> str:
        """
        Send a Slack notification.

        :param notification_data: Data required to send the Slack notification.
        :return: Provider message id
        """
        if notification_data.file_id is not None:
            return await self.send_file(
                notify_data=notification_data,
            )
        else:
            return await self.send_message(
                channel_id=notification_data.channel_id,
                text=notification_data.message,
            )

    async def send_message(self, channel_id: str, text: str) -> str:
        """
        Send a Slack message.

        :param channel_id: The ID of the channel to which we want to send the message.
        :param text: The message to send.
        :return: Provider message id
        """
        return await self._client.send_message(
            channel_id=channel_id,
            text=text,
        )

    async def send_file(
        self,
        notify_data: SlackNotificationSchema,
    ) -> str:
        """
        Send a file via Slack.

        :param notify_data: Data required to send the Slack notification.
        :return: None
        """
        file_data = await self._file_service.get_file(notify_data.file_id)

        return await self._client.send_document(
            channel_id=notify_data.channel_id,
            text=notify_data.message,
            file_name=file_data.metadata.file_name,
            content=file_data.content,
            file_size=file_data.metadata.size,
        )

    async def send_error_message_to_channel(
        self,
        error_message: str,
    ) -> None:
        """
        Sends an error message to the administrator.

        :param error_message: Error message to send to the administrator.
        :return: None
        """
        if settings.slack.error_channel_id is None:
            raise SlackErrorChannelException("ERROR_CHANNEL_ID is not configured.")
        await self._client.send_message(
            channel_id=settings.slack.error_channel_id,
            text=error_message,
        )
