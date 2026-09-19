from core import settings
from core.exceptions import TGAdminChatIdException
from infrastructure.telegram.client import TelegramClient
from schemas.notify_schema import (
    TelegramNotificationSchema,
)
from services.file_work_service import FileWorkService


class TelegramNotifyService:
    def __init__(
        self,
        client: TelegramClient,
        file_service: FileWorkService,
    ):
        self._client = client
        self._file_service = file_service

    async def send(
        self,
        notification_data: TelegramNotificationSchema,
    ) -> str:
        """
        Send a Telegram notification.

        :param notification_data: Data required to send the Telegram notification.
        :return: provider massage id
        """

        if notification_data.file_id is not None:
            return await self.send_file(notification_data)
        else:
            return await self.send_message(notification_data)

    async def send_admin_error_message(self, error_message: str) -> str:
        """
        Sends an error message to the administrator.

        :param error_message:  Error message to send to the administrator.
        :return: provider massage id
        """
        if settings.tg.admin_chat_id is None:
            raise TGAdminChatIdException("ADMIN_CHAT_ID is not configured.")

        return await self._client.send_message(
            chat_id=settings.tg.admin_chat_id,
            text=error_message,
        )

    async def send_message(self, notify_data: TelegramNotificationSchema) -> str:
        """
        Send a Telegram message.

        :param notify_data: Data required to send the Telegram message.
        :return: provider massage id
        """
        return await self._client.send_message(
            chat_id=notify_data.chat_id,
            text=notify_data.message,
            reply_markup=(
                notify_data.reply_markup.model_dump(exclude_none=True)
                if notify_data.reply_markup
                else None
            ),
        )

    async def send_file(self, notify_data: TelegramNotificationSchema) -> str:
        """
        Send a file via Telegram.

        :param notify_data: Data required to send the Telegram file.
        :return: provider massage id
        """

        file_data = await self._file_service.get_file(notify_data.file_id)

        return await self._client.send_document(
            chat_id=notify_data.chat_id,
            filename=file_data.metadata.file_name,
            content=file_data.content,
            content_type=file_data.metadata.content_type,
            caption=notify_data.message,
        )
