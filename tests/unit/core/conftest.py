from unittest.mock import AsyncMock

import pytest

from core.retry_policy import RetryPolicy


@pytest.fixture
def fake_sleep(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("core.retry_policy.asyncio.sleep", mock)
    return mock


@pytest.fixture
def retry_policy():
    return RetryPolicy(max_attempts=3, base_delay=0, jitter=False)
