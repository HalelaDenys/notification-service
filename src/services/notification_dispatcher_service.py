from schemas.notify_enums import ChannelEnum, StatusEnum
from schemas.notify_schema import (
    EmailNotificationSchema,
    NotificationRequestSchema,
    SlackNotificationSchema,
    TelegramNotificationSchema,
)
from services.broker_notify_service import BrokerNotifyService
from services.notification_service import NotificationService


class NotificationDispatcherService:
    def __init__(
        self, notify_service: NotificationService, b_service: BrokerNotifyService
    ) -> None:
        self._notify_service = notify_service
        self._b_service = b_service

    async def notification(
        self, request_data: NotificationRequestSchema, idempotency_key: str | None
    ) -> None:
        if request_data.type == "smtp":
            await self.notify_smtp(request_data, idempotency_key)
        elif request_data.type == "telegram":
            await self.notify_telegram(request_data, idempotency_key)
        elif request_data.type == "slack":
            await self.notify_slack(request_data, idempotency_key)

    async def notify_smtp(
        self, smtp_data: EmailNotificationSchema, idempotency_key: str | None = None
    ) -> None:
        payload = {
            "channel": ChannelEnum.SMTP.value,
            "subject": smtp_data.subject,
            "recipient": smtp_data.recipient,
            "status": StatusEnum.PENDING.value,
            "message": smtp_data.message,
            "idempotency_key": idempotency_key,
        }

        if smtp_data.context is not None:
            payload["payload"] = smtp_data.context.model_dump_json()

        await self._create_and_send_broker(payload=payload, notify_data=smtp_data)

    async def notify_telegram(
        self, tg_data: TelegramNotificationSchema, idempotency_key: str | None = None
    ) -> None:
        payload = {
            "channel": ChannelEnum.TELEGRAM.value,
            "recipient": str(tg_data.chat_id),
            "status": StatusEnum.PENDING.value,
            "message": tg_data.message,
            "idempotency_key": idempotency_key,
        }

        if tg_data.reply_markup is not None:
            payload["payload"] = tg_data.reply_markup.model_dump_json()

        if tg_data.file_id is not None:
            payload["file_id"] = f"{tg_data.file_id}"

        await self._create_and_send_broker(payload=payload, notify_data=tg_data)

    async def notify_slack(
        self, slack_data: SlackNotificationSchema, idempotency_key: str | None = None
    ) -> None:
        payload = {
            "channel": ChannelEnum.SLACK.value,
            "recipient": slack_data.channel_id,
            "status": StatusEnum.PENDING.value,
            "message": slack_data.message,
            "idempotency_key": idempotency_key,
        }

        if slack_data.file_id is not None:
            payload["file_id"] = f"{slack_data.file_id}"

        await self._create_and_send_broker(payload=payload, notify_data=slack_data)

    async def _create_and_send_broker(
        self, payload, notify_data: NotificationRequestSchema
    ) -> None:
        notification = await self._notify_service.save_notification(payload)

        if notification is None:
            return

        await self._b_service.send(
            data=notify_data,
        )
