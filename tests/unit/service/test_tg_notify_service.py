from unittest.mock import AsyncMock

import pytest

from core.exceptions import RetryError, TelegramClientException


class TestTgNotifyService:
    @pytest.mark.asyncio
    async def test_send_calls_client_with_plain_params(
        self, fake_tg_client, tg_service, plain_data_tg
    ):
        await tg_service.send(data=plain_data_tg)

        assert len(fake_tg_client.calls) == 1
        call = fake_tg_client.calls[0]

        assert call["chat_id"] == plain_data_tg.chat_id
        assert call["text"] == plain_data_tg.message
        assert call["reply_markup"] is None

    @pytest.mark.asyncio
    async def test_send_passes_inline_keyboard_markup(
        self, fake_tg_client, tg_service, data_with_inline_keyboard
    ):
        await tg_service.send(data=data_with_inline_keyboard)

        assert len(fake_tg_client.calls) == 1
        call = fake_tg_client.calls[0]
        data = data_with_inline_keyboard.model_dump(exclude_none=True)

        assert call["reply_markup"] == data["reply_markup"]

    @pytest.mark.asyncio
    async def test_send_passes_reply_keyboard_markup(
        self, fake_tg_client, tg_service, data_with_reply_keyboard
    ):
        await tg_service.send(data=data_with_reply_keyboard)

        assert len(fake_tg_client.calls) == 1
        call = fake_tg_client.calls[0]
        data = data_with_reply_keyboard.model_dump(exclude_none=True)

        assert call["reply_markup"] == data["reply_markup"]

    @pytest.mark.asyncio
    async def test_send_passes_none_when_no_reply_markup(
        self, fake_tg_client, tg_service, plain_data_tg
    ):
        await tg_service.send(data=plain_data_tg)

        assert fake_tg_client.calls[0]["reply_markup"] is None

    @pytest.mark.asyncio
    async def test_send_retries_on_telegram_exception(
        self, fake_tg_client, tg_service, plain_data_tg
    ):
        fake_tg_client.send_message = AsyncMock(
            side_effect=[
                TelegramClientException("error"),
                TelegramClientException("error"),
                None,
            ],
        )

        await tg_service.send(plain_data_tg)

        assert fake_tg_client.send_message.await_count == 3

    @pytest.mark.asyncio
    async def test_send_raises_retry_error_after_all_attempts(
        self, fake_tg_client, tg_service, plain_data_tg
    ):
        fake_tg_client.send_message = AsyncMock(
            side_effect=TelegramClientException("error"),
        )

        with pytest.raises(RetryError):
            await tg_service.send(plain_data_tg)

        assert fake_tg_client.send_message.await_count == 3
