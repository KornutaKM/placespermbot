import asyncio

import pytest
from aiogram.exceptions import TelegramNetworkError

from app.telegram_resilience import retry_transient_telegram


def test_transient_telegram_failure_is_retried() -> None:
    async def scenario() -> None:
        attempts = 0
        sleeps: list[float] = []

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise TelegramNetworkError(method=None, message="temporary")
            return "ok"

        async def sleep(delay: float) -> None:
            sleeps.append(delay)

        result = await retry_transient_telegram(
            operation,
            operation_name="test operation",
            sleep=sleep,
        )

        assert result == "ok"
        assert attempts == 3
        assert sleeps == [0.5, 1.0]

    asyncio.run(scenario())


def test_transient_telegram_failure_is_bounded() -> None:
    async def scenario() -> None:
        attempts = 0
        sleeps: list[float] = []

        async def operation() -> None:
            nonlocal attempts
            attempts += 1
            raise TelegramNetworkError(method=None, message="temporary")

        async def sleep(delay: float) -> None:
            sleeps.append(delay)

        with pytest.raises(TelegramNetworkError):
            await retry_transient_telegram(
                operation,
                operation_name="test operation",
                sleep=sleep,
            )

        assert attempts == 4
        assert sleeps == [0.5, 1.0, 2.0]

    asyncio.run(scenario())


def test_non_transient_failure_is_not_retried() -> None:
    async def scenario() -> None:
        attempts = 0
        sleeps: list[float] = []

        async def operation() -> None:
            nonlocal attempts
            attempts += 1
            raise ValueError("invalid local state")

        async def sleep(delay: float) -> None:
            sleeps.append(delay)

        with pytest.raises(ValueError, match="invalid local state"):
            await retry_transient_telegram(
                operation,
                operation_name="test operation",
                sleep=sleep,
            )

        assert attempts == 1
        assert sleeps == []

    asyncio.run(scenario())
