import pytest
from pytest_httpx import HTTPXMock

from core.exceptions import TelegramClientException

TOKEN = "test-token"
TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


class TestTelegramClient:
    @pytest.mark.asyncio
    async def test_send_message_builds_correct_payload(
        self, tg_client, httpx_mock: HTTPXMock, plain_data_tg
    ):
        httpx_mock.add_response(url=TELEGRAM_URL, status_code=200)

        await tg_client.send_message(
            chat_id=plain_data_tg.chat_id, text=plain_data_tg.message
        )

        response = httpx_mock.get_request()
        import json

        payload = json.loads(response.content)

        assert payload["chat_id"] == plain_data_tg.chat_id
        assert payload["text"] == plain_data_tg.message
        assert payload["parse_mode"] == "HTML"
        assert payload != "reply_markup"

    @pytest.mark.asyncio
    async def test_send_message_includes_reply_markup(
        self, tg_client, httpx_mock, data_with_inline_keyboard
    ):
        httpx_mock.add_response(url=TELEGRAM_URL, status_code=200)

        reply_markup = data_with_inline_keyboard.reply_markup.model_dump(
            mode="json", exclude_none=True
        )

        await tg_client.send_message(
            chat_id=data_with_inline_keyboard.chat_id,
            text=data_with_inline_keyboard.message,
            reply_markup=reply_markup,
        )
        response = httpx_mock.get_request()
        import json

        payload = json.loads(response.content)

        assert payload["chat_id"] == data_with_inline_keyboard.chat_id
        assert payload["text"] == data_with_inline_keyboard.message
        assert payload["parse_mode"] == "HTML"
        assert payload["reply_markup"] == reply_markup

    @pytest.mark.asyncio
    async def test_send_message_raises_on_4xx(
        self,
        tg_client,
        httpx_mock: HTTPXMock,
    ):
        httpx_mock.add_response(url=TELEGRAM_URL, status_code=400)

        with pytest.raises(TelegramClientException, match="Telegram API error: 400"):
            await tg_client.send_message(chat_id=123456789, text="Hello")

    @pytest.mark.asyncio
    async def test_send_message_raises_on_5xx(
        self,
        tg_client,
        httpx_mock: HTTPXMock,
    ):
        httpx_mock.add_response(url=TELEGRAM_URL, status_code=500)

        with pytest.raises(TelegramClientException, match="Telegram API error: 500"):
            await tg_client.send_message(chat_id=123456789, text="Hello")

    @pytest.mark.asyncio
    async def test_send_message_posts_to_correct_url(
        self,
        tg_client,
        httpx_mock: HTTPXMock,
    ):
        httpx_mock.add_response(url=TELEGRAM_URL, status_code=200)

        await tg_client.send_message(chat_id=123456789, text="Hello")

        request = httpx_mock.get_request()

        assert str(request.url) == TELEGRAM_URL
        assert request.method == "POST"
