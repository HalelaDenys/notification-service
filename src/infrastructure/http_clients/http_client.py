import json
import logging
from abc import ABC, abstractmethod
from typing import Any, NoReturn

import httpx

from core.exceptions import (
    HTTPStatusClassificationError,
    NonRetryableError,
    RetryableError,
)

_PERMANENT_HTTP_STATUS_CODES = frozenset({400, 401, 403, 404, 422, 501, 505})

_TRANSIENT_HTTP_STATUS_CODES = frozenset(
    {
        408,  # Request Timeout
        429,  # Too Many Requests
        500,
        502,
        503,
        504,
        520,  # Cloudflare errors
        521,
        522,
        523,
        524,
    }
)

_PERMANENT_EXCEPTIONS = (
    httpx.InvalidURL,
    httpx.UnsupportedProtocol,
)
logger = logging.getLogger("http.client")

# httpx logs every request at INFO level, and URLs may contain secrets.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def classify_transient_or_permanent_error_by_code(
    status_code: int,
    transient_exc: type[RetryableError],
    permanent_exc: type[NonRetryableError],
    msg: str,
    exc: Exception | None = None,
    retry_after: int | None = None,
    cause_type: str | None = None,
) -> NoReturn:
    """
    Raise the appropriate exception for an HTTP

    :param status_code: HTTP status code.
    :param transient_exc: type of transient exception.
    :param permanent_exc: type of permanent exception.
    :param msg: error message.
    :param exc: exception object.
    :param retry_after: number of seconds to retry after transient exception.
    :param cause_type: type of cause exception.
    :raises transient_exc: retry makes sense.
    :raises permanent_exc: retry is pointless.
    :raises HTTPStatusClassificationError: code could not be classified.
    """
    # transient error
    if status_code in _TRANSIENT_HTTP_STATUS_CODES or 500 <= status_code < 600:
        raise transient_exc(
            msg,
            retry_after=retry_after,
            cause_type=cause_type,
            status_code=status_code,
        ) from exc
    # permanent error
    if status_code in _PERMANENT_HTTP_STATUS_CODES or 400 <= status_code < 500:
        raise permanent_exc(
            msg, cause_type=cause_type, status_code=status_code
        ) from exc

    raise HTTPStatusClassificationError(
        f"Unclassified HTTP status code: {status_code}"
    ) from exc


class HTTPClient(ABC):
    """
    Base abstract async HTTP client for notification providers.

    Subclasses must set `transient_exc` / `permanent_exc` and implement
    `_handle_payload` (provider-specific application-level error handling).
    """

    transient_exc: type[RetryableError]
    permanent_exc: type[NonRetryableError]

    def __init__(
        self,
        url: str,
        timeout: float = 10.0,
        secrets: tuple[str, ...] = (),
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._timeout = timeout
        self._secrets = tuple(s for s in secrets if s)
        self._default_headers = default_headers or {}
        self._client: httpx.AsyncClient | None = None

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"

    async def connect(self) -> None:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout, headers=self._default_headers
            )

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            finally:
                self._client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        await self.connect()
        assert self._client is not None
        return self._client

    def _mask(self, value: object) -> str:
        """Hide secrets in any text that may be logged or raised."""
        text = str(value)
        for secret in self._secrets:
            text = text.replace(secret, "*****")
        return text

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        try:
            data = json.loads(text)
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _retry_after(response: httpx.Response, payload: dict) -> int | None:
        """
        We retrieve the “Retry-After” from the header in Slack
        or “parameters.retry_after” from the body of the Telegram request.

        :param response: HTTP response object.
        :param payload: payload object.
        :return the time when you need to make your next attempt or None.
        """
        raw = response.headers.get("Retry-After")

        if raw is None:
            parameters = payload.get("parameters")
            if isinstance(parameters, dict):
                raw = parameters.get("retry_after")

        try:
            value = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

        return value if value is not None and value >= 0 else None

    def _raise_transient(
        self,
        msg: str,
        status_code: int | None = None,
        retry_after: int | None = None,
        cause_type: str | None = None,
    ) -> NoReturn:
        """
        Raise a transient error that may be retried.

        :param msg: Error message.
        :param cause_type: type of cause exception.
        :param retry_after: Delay in seconds before the next retry.
        :raises self.transient_exc: When a retryable error occurs.
        """

        raise self.transient_exc(
            msg,
            retry_after=retry_after,
            cause_type=cause_type,
            status_code=status_code,
        ) from None

    def _raise_permanent(
        self,
        msg: str,
        status_code: int | None = None,
        cause_type: str | None = None,
    ) -> NoReturn:
        """
        Raise a permanent error that should not be retried.

        :param msg: Error message.
        :param cause_type: type of cause exception.
        :raises self.permanent_exc: When a non-retryable error occurs.
        """
        raise self.permanent_exc(
            msg, cause_type=cause_type, status_code=status_code
        ) from None

    async def _post(
        self,
        method: str,
        *,
        json_body: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """
        Call `{url}/{method}`, handle transport/HTTP errors and delegate
        application-level checks to `_handle_payload`.


        :param method: the method we want to call: url + /method
        :param json_body: data to be transferred
        :param data: data to be transferred
        :param files: files to be transferred
        :param headers:
        :raises transient_exc: network problem or retryable API error.
        :raises permanent_exc: invalid request or non-retryable API error.
        :raises HTTPStatusClassificationError: unknown HTTP status code.
        """

        # connection check
        client = await self._ensure_client()

        try:
            response = await client.post(
                f"{self._url}/{method}",
                json=json_body,
                data=data,
                files=files,
                headers=headers,
            )
            response.raise_for_status()
        # error handling by status code (retryable / no retryable)
        except httpx.HTTPStatusError as exc:
            resp = exc.response
            body = resp.text
            payload = self._parse_json(body) or {}
            classify_transient_or_permanent_error_by_code(
                status_code=resp.status_code,
                transient_exc=self.transient_exc,
                permanent_exc=self.permanent_exc,
                msg=f"API error ({resp.status_code}) on {method}: {self._mask(body)}",
                retry_after=self._retry_after(resp, payload),
                cause_type=type(exc).__name__,
            )
        # handling of permanent error (no retryable)
        except _PERMANENT_EXCEPTIONS as exc:
            self._raise_permanent(
                f"Request configuration error: {self._mask(exc)}",
                cause_type=type(exc).__name__,
            )
        # handling of transient error (retryable)
        # connection errors, timeouts, network errors, etc.
        except httpx.RequestError as exc:
            self._raise_transient(
                f"Network error on {method}: {type(exc).__name__}: {self._mask(exc)}",
                cause_type=type(exc).__name__,
            )
        # handling of unclassified errors
        except httpx.HTTPError as exc:
            logger.warning(
                "Unclassified http error on %s, treating as transient: %s",
                method,
                self._mask(exc),
            )
            self._raise_transient(
                f"Unclassified API error on {method}: {self._mask(exc)}",
                cause_type=type(exc).__name__,
            )

        payload = self._parse_json(response.text)
        if payload is None:
            self._raise_transient(
                f"Invalid JSON in response on method {method}, "
                f"(status={response.status_code})",
                status_code=response.status_code,
            )
        return self._handle_payload(method, payload, response)

    @abstractmethod
    def _handle_payload(
        self,
        method: str,
        payload: dict,
        response: httpx.Response,
    ) -> Any:
        """
        Check the provider-specific "ok/error" contract of a 2xx response.

        Must return the useful data or raise via `_raise_transient`,
        `_raise_permanent` or `classify_transient_or_permanent_error_by_code`.
        """
        raise NotImplementedError
