from unittest.mock import Mock

import pytest

from core.exceptions import RetryError
from core.retry_policy import RetryPolicy


class TestRetryPolicy:
    @pytest.mark.asyncio
    async def test_execute_success_first_attempt(self, retry_policy):
        async def handler():
            return "oK"

        result = await retry_policy.execute(handler)

        assert result == "oK"

    @pytest.mark.asyncio
    async def test_execute_success_after_retries(
        self,
        retry_policy,
        fake_sleep,
    ):
        attempts = 0

        async def handler():
            nonlocal attempts
            attempts += 1

            if attempts < 3:
                raise ValueError("error")

            return "success"

        result = await retry_policy.execute(handler)

        assert result == "success"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_execute_exhausted_retries(self, retry_policy, fake_sleep):
        attempts = 0

        async def handler():
            nonlocal attempts
            attempts += 1
            raise ValueError("error")

        with pytest.raises(RetryError) as exc_info:
            await retry_policy.execute(handler)

        assert attempts == 3
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_calculate_delay_without_jitter(self):
        retry_policy = RetryPolicy(
            base_delay=1,
            max_delay=100,
            jitter=False,
        )

        assert retry_policy._calculate_delay(1) == 1
        assert retry_policy._calculate_delay(2) == 2
        assert retry_policy._calculate_delay(3) == 4
        assert retry_policy._calculate_delay(4) == 8
        assert retry_policy._calculate_delay(5) == 16

    def test_calculate_delay_respects_max_delay(self):
        retry_policy = RetryPolicy(
            base_delay=10,
            max_delay=15,
            jitter=False,
        )

        assert retry_policy._calculate_delay(1) == 10
        assert retry_policy._calculate_delay(2) == 15
        assert retry_policy._calculate_delay(3) == 15

    def test_calculate_delay_with_jitter(self, monkeypatch):
        retry_policy = RetryPolicy(
            base_delay=10,
            max_delay=15,
            jitter=True,
        )

        uniform_mock = Mock(return_value=1.2)

        monkeypatch.setattr(
            "core.retry_policy.random.uniform",
            uniform_mock,
        )

        delay = retry_policy._calculate_delay(1)

        assert delay == 12
