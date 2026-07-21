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
    ) -> None:
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

    async def send_document(
        self,
        chat_id: int,
        filename: str,
        content: bytes,
        content_type: str,
        caption: str | None = None,
    ) -> None:
        """
        sends a document/file via the self._url/sendDocument Telegram Bot API
        :param chat_id: Recipient’s chat ID
        :param filename: File name
        :param caption: Additional text for the file
        :param content: Content for the file
        :param content_type: Content type
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
