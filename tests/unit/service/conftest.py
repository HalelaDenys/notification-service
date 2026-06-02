from unittest.mock import AsyncMock

import pytest

from services.broker_notify_service import BrokerNotifyService


@pytest.fixture()
def mock_broker():
    mock_broker = AsyncMock()
    return mock_broker


@pytest.fixture()
def broker_notify_service(mock_broker):
    service = BrokerNotifyService(broker=mock_broker)
    return service
