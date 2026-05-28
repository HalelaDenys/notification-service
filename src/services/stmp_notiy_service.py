from infrastructure import SMTPClient, template
from schemas.notify_schema import EmailNotificationSchema


class STMPNotifyService:
    def __init__(self, smtp_client: SMTPClient):
        self._smtp_client = smtp_client

    async def send(self, data: EmailNotificationSchema) -> None:
        if data.context:
            await self._send_html(data)
        else:
            await self._send_plain(data)

    async def _send_plain(self, data: EmailNotificationSchema) -> None:
        await self._smtp_client.send_email(
            recipient=data.recipient,
            subject=data.subject,
            plain_content=data.message,
        )

    def _render_html(self, data: EmailNotificationSchema) -> str:
        context = data.context
        if context is None:
            raise ValueError("Context is required for HTML rendering")

        tmp = template.get_template("email/notification.html")

        return tmp.render(
            title=context.title,
            subject=data.subject,
            message=data.message,
            action_url=context.action_url,
            action_text=context.action_text,
            preheader=context.preheader,
            recipient=data.recipient,
        )

    async def _send_html(self, data: EmailNotificationSchema) -> None:
        html = self._render_html(data)

        await self._smtp_client.send_email(
            recipient=data.recipient,
            subject=data.subject,
            plain_content=data.message,
            html_content=html,
        )
