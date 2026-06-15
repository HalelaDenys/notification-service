import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from core.exceptions import RetryError

logger = logging.getLogger(__name__)
T = TypeVar("T")


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        exceptions: tuple[type[Exception], ...] = (Exception,),
        jitter: bool = True,
    ):
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._exceptions = exceptions
        self._jitter = jitter

    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs,
    ) -> T:
        last_error = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except self._exceptions as exc:
                last_error = exc

                if attempt == self._max_attempts:
                    break

                delay = self._calculate_delay(attempt)

                logger.warning(
                    "Retry attempt %s/%s failed: %s. Next retry in %.2fs",
                    attempt,
                    self._max_attempts,
                    exc,
                    delay,
                )

                await asyncio.sleep(delay)

        logger.error(
            "All %s attempts exhausted. Last error: %s",
            self._max_attempts,
            last_error,
        )
        raise RetryError(
            f"Operation failed after {self._max_attempts} attempts"
        ) from last_error

    def _calculate_delay(self, attempt: int) -> float:
        delay = self._base_delay * (2 ** (attempt - 1))

        if self._jitter:
            delay *= random.uniform(0.7, 1.3)

        return min(delay, self._max_delay)
