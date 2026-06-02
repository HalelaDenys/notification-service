import pytest
import pytest_asyncio
from faststream.redis import TestRedisBroker

from workers import smtp_worker


@pytest_asyncio.fixture()
async def test_smtp_broker():
    async with TestRedisBroker(smtp_worker.broker) as br:
        yield br


@pytest.fixture()
def patched_notify_service(fake_notify_service, monkeypatch):
    monkeypatch.setattr(smtp_worker, "service", fake_notify_service)
    return fake_notify_service
