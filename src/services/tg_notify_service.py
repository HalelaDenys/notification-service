from core.retry_policy import RetryPolicy
from infrastructure.telegram.client import TelegramClient
from schemas.notify_schema import TelegramNotificationSchema


class TelegramNotifyService:
    def __init__(self, client: TelegramClient, retry_policy: RetryPolicy):
        self._client = client
        self._retry_policy = retry_policy

    async def send(self, data: TelegramNotificationSchema) -> None:
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
