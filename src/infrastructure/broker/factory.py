from faststream.redis import RedisBroker

from core import settings


def create_redis_broker() -> RedisBroker:
    return RedisBroker(settings.redis.dsn)
