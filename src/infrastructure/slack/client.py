import httpx

from core.exceptions import SlackClientException


class SlackClient:
    """Slack client class."""

    def __init__(self, token: str, timeout: float = 10.0):
        self._token = token
        self._timeout = timeout
        self._url = "https://slack.com/api"

    async def send_message(self, channel_id: str, text: str) -> str:
        """
        Send a message to a Slack channel.

        :param channel_id: Identifier of the Slack channel.
        :param text: Text of the message to send.
        :return: Timestamp of the published Slack message.
        """

        payload = {"channel": channel_id, "text": text}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._url}/chat.postMessage",
                json=payload,
                headers=self._get_json_headers(),
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

            return data["ts"]

    async def send_document(
        self,
        channel_id: str,
        text: str,
        file_name: str,
        content: bytes,
        file_size: int,
    ) -> str:
        """
        Send a document to a Slack channel.

        :param channel_id: Identifier of the Slack channel.
        :param text: Optional text to include with the document.
        :param file_name: Name of the file to send.
        :param content: File content to upload.
        :param file_size: Size of the file in bytes.
        :return: Timestamp of the published Slack message.
        """

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            upload_url, file_id = await self._get_upload_url(
                client=client,
                file_name=file_name,
                file_size=file_size,
            )

            await self._upload_file(
                client=client,
                file_name=file_name,
                upload_url=upload_url,
                content=content,
            )

            return await self._complete_upload(
                client=client,
                file_id=file_id,
                file_name=file_name,
                channel_id=channel_id,
                comment=text,
            )

    async def _get_upload_url(
        self,
        client: httpx.AsyncClient,
        file_name: str,
        file_size: int,
    ) -> tuple[str, str]:
        """
        Retrieve a one-time URL for uploading a file.

        :param client: HTTP client used to send the request.
        :param file_name: Name of the file to upload.
        :param file_size: Size of the file in bytes.
        :return: Tuple containing the upload URL and file ID.
        """

        response = await client.post(
            f"{self._url}/files.getUploadURLExternal",
            headers=self._get_auth_headers(),
            data={"filename": file_name, "length": file_size},
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):
            raise SlackClientException(data.get("error", "Unknown Slack error"))

        return data["upload_url"], data["file_id"]

    async def _upload_file(
        self,
        client: httpx.AsyncClient,
        file_name: str,
        upload_url: str,
        content: bytes,
    ) -> None:
        """
        Upload a file to the provided upload URL.

        :param client: HTTP client used to send the request.
        :param file_name: Name of the file to upload.
        :param upload_url: One-time URL used to upload the file.
        :param content: File content to upload.
        :return: None
        """

        response = await client.post(
            upload_url,
            files={
                "file": (file_name, content),
            },
        )

        response.raise_for_status()

    async def _complete_upload(
        self,
        client: httpx.AsyncClient,
        file_id: str,
        file_name: str,
        channel_id: str,
        comment: str | None = None,
    ) -> str:
        """
        Complete a file upload and publish the file to a Slack channel.

        :param client: HTTP client used to send the request.
        :param file_id: Identifier of the uploaded file.
        :param file_name: Name of the file to publish.
        :param channel_id: Identifier of the Slack channel.
        :param comment: Optional comment to include with the file.
        :return: Timestamp of the published Slack message.
        """

        response = await client.post(
            f"{self._url}/files.completeUploadExternal",
            headers=self._get_auth_headers(),
            json={
                "files": [
                    {
                        "id": file_id,
                        "title": file_name,
                    }
                ],
                "channel_id": channel_id,
                "initial_comment": comment,
            },
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):
            raise SlackClientException(data.get("error", "Unknown Slack error"))

        return str(data["ts"])

    def _get_auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
        }

    def _get_json_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
