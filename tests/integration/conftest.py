from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from create_app import create_app
from dependencies import get_notify_service


@pytest.fixture()
def app(fake_notify_service):
    app = create_app()
    app.dependency_overrides[get_notify_service] = lambda: fake_notify_service

    yield app

    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    async with client_manager(app) as client:
        yield client


@asynccontextmanager
async def client_manager(
    app,
    base_url: str = "http://test",
    **kwargs,
) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)

    async with AsyncClient(
        transport=transport,
        base_url=base_url,
        **kwargs,
    ) as client:
        yield client
