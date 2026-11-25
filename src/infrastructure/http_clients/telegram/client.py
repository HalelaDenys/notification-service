import logging

import httpx

from core.exceptions import (
    TelegramClientException,
    TelegramPermanentError,
    TelegramTransientError,
)
from infrastructure.http_clients.http_client import (
    HTTPClient,
    classify_transient_or_permanent_error_by_code,
)
from schemas.dtos import TelegramNotificationDTO

logger = logging.getLogger("telegram.client")


class TelegramClient(HTTPClient):
    transient_exc = TelegramTransientError
    permanent_exc = TelegramPermanentError

    def __init__(self, token: str, timeout: float = 10.0):
        super().__init__(
            url=f"https://api.telegram.org/bot{token}/",
            timeout=timeout,
            secrets=(token,),
        )

    def _handle_payload(
        self,
        method: str,
        payload: dict,
        response: httpx.Response,
    ) -> dict | None:
        if payload.get("ok"):
            return payload.get("result")

        error_code = payload.get("error_code", response.status_code)
        classify_transient_or_permanent_error_by_code(
            status_code=error_code,
            transient_exc=self.transient_exc,
            permanent_exc=self.permanent_exc,
            msg=f"Transient Telegram API error: ({error_code}) on {method}"
            f"{payload.get('description', 'Unknown error')}",
            retry_after=self._retry_after(response, payload),
            cause_type="TelegramAPIError",
        )

    async def send(self, notification_data: TelegramNotificationDTO) -> str:
        """
        Send a document if filename and content are present, otherwise a text message.

        :param notification_data:

        :return: Identifier of the sent Telegram message.
        :raises TelegramTransientError: retryable failure.
        :raises TelegramPermanentError: non-retryable failure.
        """

        if notification_data.filename and notification_data.content:
            return await self._send_document(
                chat_id=notification_data.chat_id,
                filename=notification_data.filename,
                content=notification_data.content,
                content_type=notification_data.content_type,
                caption=notification_data.caption,
            )
        return await self._send_message(
            chat_id=notification_data.chat_id,
            text=notification_data.content,
            parse_mode=notification_data.parse_mode,
            reply_markup=notification_data.reply_markup,
        )

    async def _send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: dict | None = None,
    ) -> str:
        """
        Send a message via the Telegram Bot API.

        :param chat_id: Recipient's chat ID.
        :param text: Text of the message.
        :param parse_mode: Formatting mode for the message text.
        :param reply_markup: Optional inline keyboard or reply markup.

        :return: Identifier of the sent Telegram message.

        :raises TelegramTransientError: retryable failure.
        :raises TelegramPermanentError: non-retryable failure.
        :raises HTTPStatusClassificationError: unknown HTTP status code.
        """

        payload = {
            "chat_id": chat_id,
            "text": text,
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode

        result = await self._post(
            "sendMessage",
            json_body=payload,
        )
        try:
            return str(result["message_id"])
        except (KeyError, TypeError) as exc:
            logger.warning(
                "Unexpected response shape on sendDocument: %s", self._mask(exc)
            )
            raise TelegramClientException(
                "Unexpected response shape on sendMessage",
                cause_type=type(exc).__name__,
            )

    async def _send_document(
        self,
        chat_id: int,
        filename: str,
        content: bytes,
        content_type: str,
        caption: str | None = None,
        parse_mode: str | None = None,
    ) -> str:
        """
        Send a document via the Telegram Bot API.

        :param chat_id: Recipient's chat ID.
        :param filename: Name of the file.
        :param content: File content.
        :param content_type: MIME type of the file.
        :param caption: Optional text to include with the file.
        :param parse_mode: Formatting mode for the file content.

        :return: Identifier of the sent Telegram message.

        :raises TelegramTransientError: retryable failure.
        :raises TelegramPermanentError: non-retryable failure.
        :raises HTTPStatusClassificationError: unknown HTTP status code.
        """
        if isinstance(content, str):
            content = content.encode("utf-8")

        data = {
            "chat_id": str(chat_id),
        }
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode

        files = {
            "document": (filename, content, content_type or "application/octet-stream")
        }

        result = await self._post(
            "sendDocument",
            data=data,
            files=files,
        )
        try:
            return str(result["message_id"])
        except (KeyError, TypeError) as exc:
            logger.warning(
                "Unexpected response shape on sendDocument: %s", self._mask(exc)
            )
            raise TelegramClientException(
                "Unexpected response shape on sendDocument",
                cause_type=type(exc).__name__,
            )
