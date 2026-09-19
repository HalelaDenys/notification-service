import httpx

from core.exceptions import TelegramClientException


class TelegramClient:
    def __init__(self, token: str, timeout: float = 10.0):
        self._token = token
        self._timeout = timeout
        self._url = f"https://api.telegram.org/bot{self._token}"

    async def send_message(
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
        """

        payload = {
            "chat_id": chat_id,
            "parse_mode": parse_mode,
            "text": text,
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url=f"{self._url}/sendMessage",
                json=payload,
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise TelegramClientException(
                    f"Telegram API error: {exc.response.status_code}"
                ) from exc

            data = response.json()

            if not data.get("ok"):
                raise TelegramClientException(
                    f"Telegram API error: {data.get('description')}"
                )

            return str(response.json()["result"]["message_id"])

    async def send_document(
        self,
        chat_id: int,
        filename: str,
        content: bytes,
        content_type: str,
        caption: str | None = None,
    ) -> str:
        """
        Send a document via the Telegram Bot API.

        :param chat_id: Recipient's chat ID.
        :param filename: Name of the file.
        :param content: File content.
        :param content_type: MIME type of the file.
        :param caption: Optional text to include with the file.
        :return: Identifier of the sent Telegram message.
        """

        payload = {
            "chat_id": str(chat_id),
        }

        if caption:
            payload["caption"] = caption

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                url=f"{self._url}/sendDocument",
                data=payload,
                files={"document": (filename, content, content_type)},
            )

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise TelegramClientException(
                    f"Telegram API error {exc.response.status_code}: "
                    f"{exc.response.text}"
                ) from exc

            data = response.json()
            if not data.get("ok"):
                raise TelegramClientException(
                    f"Telegram API error: {data.get('description')}"
                )
            return str(response.json()["result"]["message_id"])
