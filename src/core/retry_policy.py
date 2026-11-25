import logging
import random
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar

from core.exceptions import RetryableError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryPolicy:
    """
    Computes retry parameters for a single attempt. Does NOT sleep and
    does NOT loop — the caller performs one attempt at a time, and a
    retry is scheduled via next_retry_at in the DB, picked up later by
    the relay.
    """

    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        retryable_exceptions: tuple[type[RetryableError], ...] = (RetryableError,),
        jitter: bool = True,
    ):
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._retryable_exceptions = retryable_exceptions
        self._jitter = jitter

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    def is_retryable(self, error: RetryableError | Exception) -> bool:
        return isinstance(error, self._retryable_exceptions)

    def next_daley(self, attempt: int) -> float:
        delay = self._base_delay * (2 ** (attempt - 1))
        if self._jitter:
            delay *= random.uniform(0.7, 1.3)
        return min(delay, self._max_delay)

    @staticmethod
    async def execute_once(
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs,
    ) -> tuple[T | None, Exception | None, datetime, datetime]:
        started_at = datetime.now(UTC)
        try:
            result = await func(*args, **kwargs)
            return result, None, started_at, datetime.now(UTC)
        except Exception as exc:
            return None, exc, started_at, datetime.now(UTC)
