import httpx

from core.exceptions import TelegramClientException


class TelegramClient:
    def __init__(self, token: str, timeout: float = 10.0):
        self._token = token
        self._timeout = timeout
        self._url = f"https://api.telegram.org/bot{self._token}/sendMessage"

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
                url=self._url,
                json=payload,
            )

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise TelegramClientException(
                    f"Telegram API error: {exc.response.status_code}"
                ) from exc
