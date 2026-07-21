import logging

from redis.asyncio import Redis

from core import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, url: str) -> None:
        self.url = url
        self._redis: Redis | None = None

    async def connect(self) -> None:
        if self._redis is not None:
            return

        self._redis = Redis.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await self._redis.ping()
            logger.info("Successfully connected Redis")
        except Exception as exc:
            await self._redis.aclose()
            self._redis = None
            logger.error("Failed to connect to Redis: %s", exc)
            raise

    async def disconnect(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("Disconnected Redis")

    @property
    def client(self) -> Redis:
        if self._redis is None:
            raise RuntimeError("Redis client is not initialized. Call connect() first.")
        return self._redis


redis_client = RedisClient(
    url=settings.redis.dsn,
)
