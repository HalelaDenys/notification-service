import httpx

from core.exceptions import SlackClientException


class SlackClient:
    """Slack client class."""

    def __init__(self, token: str, timeout: float = 10.0):
        self._token = token
        self._timeout = timeout
        self._url = "https://slack.com/api"

    async def send_message(self, channel_id: str, text: str) -> None:
        """chat.postMessage"""

        payload = {"channel": channel_id, "text": text}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._url}/chat.postMessage",
                json=payload,
                headers=self._get_headers(),
            )

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise SlackClientException(
                    f"Slack API error: {exc.response.status_code}"
                ) from exc

            data = response.json()

            if not data.get("ok"):
                raise SlackClientException(f"Slack API error: {data.get('error')}")

    async def send_file(self, channel_id: str, text: str, file_path: str) -> None:
        raise NotImplementedError("send_file is not implemented yet")

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
