import logging

import httpx

from core.exceptions import (
    SlackClientException,
    SlackPermanentError,
    SlackTransientError,
)
from infrastructure.http_clients.http_client import HTTPClient
from schemas.dtos import SlackNotificationDTO

logger = logging.getLogger("slack.client")


_TRANSIENT_SLACK_ERRORS = frozenset(
    {
        "ratelimited",
        "rate_limited",
        "internal_error",
        "fatal_error",
        "service_unavailable",
        "request_timeout",
    }
)


class SlackClient(HTTPClient):
    """Slack client class."""

    transient_exc = SlackTransientError
    permanent_exc = SlackPermanentError

    def __init__(self, token: str, timeout: float = 10.0):
        super().__init__(
            url="https://slack.com/api",
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
            return payload

        error = payload.get("error", "unknown_error")
        msg = f"Slack API error on {method}: {error}"

        if error in _TRANSIENT_SLACK_ERRORS:
            self._raise_transient(
                msg=msg,
                retry_after=self._retry_after(response, payload),
            )
        self._raise_permanent(msg=msg)

    async def send(self, notification_data: SlackNotificationDTO) -> str:
        if (
            notification_data.file_name
            and notification_data.content
            and notification_data.file_size
        ):
            return self._send_document(
                channel_id=notification_data.channel_id,
                text=notification_data.text,
                file_name=notification_data.file_name,
                content=notification_data.content,
                file_size=notification_data.file_size,
            )
        return self._send_message(
            channel_id=notification_data.channel_id,
            text=notification_data.text,
        )

    async def _send_message(self, channel_id: str, text: str) -> str:
        """
        Send a message to a Slack channel.

        :param channel_id: Identifier of the Slack channel.
        :param text: Text of the message to send.
        :return: Timestamp of the published Slack message.
        """

        payload = {"channel": channel_id, "text": text}

        result = await self._post(
            method="chat.postMessage",
            json_body=payload,
            headers=self._get_auth_headers(),
        )

        try:
            return str(result["ts"])
        except (KeyError, TypeError) as exc:
            logger.warning(
                "Unexpected response shape on postMessage: %s", self._mask(exc)
            )
            raise SlackClientException(
                "Unexpected response shape on postMessage",
                cause_type=type(exc).__name__,
            )

    async def _send_document(
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

        upload_url, file_id = await self._get_upload_url(
            file_name=file_name,
            file_size=file_size,
        )

        await self._upload_file(
            file_name=file_name,
            upload_url=upload_url,
            content=content,
        )

        return await self._complete_upload(
            file_id=file_id,
            file_name=file_name,
            channel_id=channel_id,
            comment=text,
        )

    async def _get_upload_url(
        self,
        # client: httpx.AsyncClient,
        file_name: str,
        file_size: int,
    ) -> tuple[str, str]:
        """
        Retrieve a one-time URL for uploading a file.

        :param file_name: Name of the file to upload.
        :param file_size: Size of the file in bytes.
        :return: Tuple containing the upload URL and file ID.
        """

        result = await self._post(
            "files.getUploadURLExternal",
            headers=self._get_auth_headers(),
            data={"filename": file_name, "length": file_size},
        )

        try:
            return result["upload_url"], result["file_id"]
        except (KeyError, TypeError) as exc:
            logger.warning(
                "Unexpected response shape on files.getUploadURLExternal: %s",
                self._mask(exc),
            )
            raise SlackClientException(
                "Unexpected response shape on files.getUploadURLExternal",
                cause_type=type(exc).__name__,
            )

    async def _upload_file(
        self,
        file_name: str,
        upload_url: str,
        content: bytes,
    ) -> None:
        """
        Upload a file to the provided upload URL.

        :param file_name: Name of the file to upload.
        :param upload_url: One-time URL used to upload the file.
        :param content: File content to upload.
        :return: Timestamp of the published Slack message
        """

        await self._post(
            upload_url,
            files={
                "file": (file_name, content),
            },
        )

    async def _complete_upload(
        self,
        file_id: str,
        file_name: str,
        channel_id: str,
        comment: str | None = None,
    ) -> str:
        """
        Complete a file upload and publish the file to a Slack channel.

        :param file_id: Identifier of the uploaded file.
        :param file_name: Name of the file to publish.
        :param channel_id: Identifier of the Slack channel.
        :param comment: Optional comment to include with the file.
        :return: Timestamp of the published Slack message.
        """

        result = await self._post(
            "files.completeUploadExternal",
            headers=self._get_auth_headers(),
            json_body={
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

        try:
            return str(result["ts"])
        except (KeyError, TypeError) as exc:
            logger.warning(
                "Unexpected response shape on files.completeUploadExternal: %s",
                self._mask(exc),
            )
            raise SlackClientException(
                "Unexpected response shape on files.completeUploadExternal",
                cause_type=type(exc).__name__,
            )

    def _get_auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {''.join(self._secrets)}",
        }

    def _get_json_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {''.join(self._secrets)}",
            "Content-Type": "application/json",
        }
