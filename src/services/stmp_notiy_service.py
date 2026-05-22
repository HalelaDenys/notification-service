from infrastructure.smtp.client import SMTPClient
from schemas.notify_schema import EmailNotificationSchema


class STMPNotifyService:
    def __init__(self, stmp_client: SMTPClient):
        self._stmp_client = stmp_client

    async def send(self, data: EmailNotificationSchema) -> None:
        await self._stmp_client.send_email(
            recipient=data.recipient,
            subject=data.subject,
            plain_content=data.message,
        )
