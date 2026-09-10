from infrastructure import SMTPClient, template
from schemas.notify_schema import EmailNotificationSchema


class SMTPNotifyService:
    def __init__(self, smtp_client: SMTPClient):
        self._smtp_client = smtp_client

    async def send(self, notify_data: EmailNotificationSchema) -> None:
        """
        Send an email notification

        :param notify_data: Data required to send the Email notification.
        :return:
        """
        if notify_data.context:
            await self._send_html(notify_data)
        else:
            await self._send_plain(notify_data)

    async def _send_plain(self, notify_data: EmailNotificationSchema) -> None:
        """
        Send a plain-text email.

        :param notify_data: Data required to send the email.
        :return: None
        """

        await self._smtp_client.send_email(
            recipient=notify_data.recipient,
            subject=notify_data.subject,
            plain_content=notify_data.message,
        )

    async def _send_html(self, notify_data: EmailNotificationSchema) -> None:
        """
        Send an HTML email.

        :param notify_data: Data required to send the email.
        :return: None
        """

        html = self._render_html(notify_data)

        await self._smtp_client.send_email(
            recipient=notify_data.recipient,
            subject=notify_data.subject,
            plain_content=notify_data.message,
            html_content=html,
        )

    @staticmethod
    def _render_html(notify_data: EmailNotificationSchema) -> str:
        """
        Render an HTML email from the notification data.

        :param notify_data: Data required to render the email.
        :return: Rendered HTML content.
        """

        context = notify_data.context
        if context is None:
            raise ValueError("Context is required for HTML rendering")

        tmp = template.get_template("email/notification.html")

        return tmp.render(
            title=context.title,
            subject=notify_data.subject,
            message=notify_data.message,
            action_url=context.action_url,
            action_text=context.action_text,
            preheader=context.preheader,
            recipient=notify_data.recipient,
        )
