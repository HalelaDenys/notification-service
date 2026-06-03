import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import pytest_asyncio
from asgi_lifespan import LifespanManager
from faststream.redis import TestRedisBroker
from httpx import ASGITransport, AsyncClient

from create_app import create_app
from workers import smtp_worker

MAILDEV_API = "http://localhost:1080"


@pytest_asyncio.fixture()
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    async with client_manager(app) as client:
        yield client


@pytest_asyncio.fixture(autouse=True)
async def real_smtp_broker():
    async with TestRedisBroker(smtp_worker.broker, with_real=True) as br:
        yield br


@pytest_asyncio.fixture(autouse=True)
async def clear_maildev():
    async with httpx.AsyncClient() as client:
        await client.delete(f"{MAILDEV_API}/email/all")
    yield


@asynccontextmanager
async def client_manager(
    app,
    base_url: str = "http://test",
    **kwargs,
) -> AsyncGenerator[AsyncClient, None]:
    app.state.testing = True
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url=base_url, **kwargs
        ) as client:
            yield client


async def wait_for_emails(
    count: int = 1,
    timeout: float = 10.0,
    maildev_url: str = MAILDEV_API,
) -> list:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    async with httpx.AsyncClient() as client:
        while loop.time() < deadline:
            response = await client.get(f"{maildev_url}/email")
            emails = response.json()
            if len(emails) >= count:
                return emails
            await asyncio.sleep(0.5)

    raise TimeoutError(f"Expected {count} emails, got {len(emails)}")
