from infrastructure import broker
from services.broker_notify_service import BrokerNotifyService


def get_notify_service() -> BrokerNotifyService:
    return BrokerNotifyService(broker=broker)
