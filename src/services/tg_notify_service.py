from core import RetryPolicy, settings
from core.exceptions import TGAdminChatIdException
from infrastructure.telegram.client import TelegramClient
from schemas.notify_schema import TelegramNotificationSchema
from services.file_work_service import FileWorkService


class TelegramNotifyService:
    def __init__(
        self,
        client: TelegramClient,
        retry_policy: RetryPolicy,
        file_service: FileWorkService,
    ):
        self._client = client
        self._retry_policy = retry_policy
        self._file_service = file_service

    async def send(self, data: TelegramNotificationSchema) -> None:
        if data.file_id is not None:
            await self.send_file(data)
        else:
            await self.send_message(data)

    async def send_admin_error_message(self, error_message: str) -> None:
        if settings.tg.admin_chat_id is None:
            raise TGAdminChatIdException("ADMIN_CHAT_ID is not configured.")

        await self._retry_policy.execute(
            self._client.send_message,
            chat_id=settings.tg.admin_chat_id,
            text=error_message,
        )

    async def send_message(self, data: TelegramNotificationSchema) -> None:
        await self._retry_policy.execute(
            self._client.send_message,
            chat_id=data.chat_id,
            text=data.message,
            reply_markup=(
                data.reply_markup.model_dump(exclude_none=True)
                if data.reply_markup
                else None
            ),
        )

    async def send_file(self, data: TelegramNotificationSchema) -> None:
        content, meta = await self._file_service.get_file(data.file_id)
        await self._retry_policy.execute(
            self._client.send_document,
            chat_id=data.chat_id,
            filename=meta["file_name"],
            content=content,
            content_type=meta["content_type"],
            caption=data.message,
        )
