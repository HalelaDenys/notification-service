from faststream.redis import RedisBroker

from core import settings

broker = RedisBroker(settings.redis.dsn)
