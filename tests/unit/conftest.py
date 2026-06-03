from unittest.mock import AsyncMock

import aiosmtplib
import pytest_asyncio

from infrastructure import SMTPClient


# SMTPClient fixture
@pytest_asyncio.fixture()
async def smtp_send_mock(monkeypatch) -> AsyncMock:
    smtp_send = AsyncMock()
    monkeypatch.setattr(aiosmtplib, "send", smtp_send)
    return smtp_send


@pytest_asyncio.fixture()
async def smtp_client() -> SMTPClient:
    return SMTPClient(
        host="localhost",
        port=1025,
        username="user",
        password="secret",
        use_tls=False,
        sender="admin@example.com",
        start_tls=True,
        timeout=5.0,
    )
