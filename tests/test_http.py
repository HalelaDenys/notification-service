import httpx
import pytest

from core.exceptions import (
    TelegramClientException,
    TelegramPermanentError,
    TelegramTransientError,
)
from infrastructure.http_clients.telegram.client import TelegramClient

TOKEN = "123456:SECRET"


def make_client(handler) -> TelegramClient:
    client = TelegramClient(token=TOKEN)
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return client


async def test_429_retry_after():
    def handler(request):
        return httpx.Response(
            429,
            json={
                "ok": False,
                "error_code": 429,
                "description": "Too Many Requests",
                "parameters": {"retry_after": 7},
            },
        )

    with pytest.raises(TelegramTransientError) as e:
        await make_client(handler).send_message(1, "hi")

    assert e.value.retry_after == 7
    assert e.value.status_code == 429


async def test_network_error_no_token_leak():
    def handler(request):
        raise httpx.ConnectTimeout("timeout", request=request)

    with pytest.raises(TelegramTransientError) as e:
        await make_client(handler).send_message(1, "hi")

    assert e.value.cause_type == "ConnectTimeout"
    assert TOKEN not in str(e.value)
    assert e.value.__cause__ is None
    assert e.value.__suppress_context__ is True


async def test_403_is_permanent():
    def handler(request):
        return httpx.Response(
            403, json={"ok": False, "error_code": 403, "description": "Forbidden"}
        )

    with pytest.raises(TelegramPermanentError) as e:
        await make_client(handler).send_message(1, "hi")

    assert e.value.status_code == 403


async def test_non_json_200_is_transient():
    def handler(request):
        return httpx.Response(200, text="<html>captive portal</html>")

    with pytest.raises(TelegramTransientError):
        await make_client(handler).send_message(1, "hi")


async def test_ok_false_with_http_200():
    # ветка _handle_payload (основная для Slack, страховочная для Telegram)
    def handler(request):
        return httpx.Response(
            200,
            json={"ok": False, "error_code": 400, "description": "Bad Request"},
        )

    with pytest.raises(TelegramPermanentError):
        await make_client(handler).send_message(1, "hi")


async def test_malformed_success_response():
    def handler(request):
        return httpx.Response(200, json={"ok": True, "result": {}})

    with pytest.raises(TelegramClientException) as e:
        await make_client(handler).send_message(1, "hi")

    assert e.value.cause_type == "KeyError"


async def test_send_document_str_content():
    def handler(request):
        assert b"hello" in request.content  # файл ушёл в multipart
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    msg_id = await make_client(handler).send_document(
        chat_id=1, filename="a.txt", content="hello", content_type="text/plain"
    )
    assert msg_id == "42"


# async def test_unclassified_status():
#     def handler(request):
#         return httpx.Response(302, headers={"Location": "https://example.com"})
#
#     with pytest.raises(HTTPStatusClassificationError) as e:
#         await make_client(handler).send_message(1, "hi")
#
#     assert e.value.status_code == 302
