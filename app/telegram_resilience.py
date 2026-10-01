from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from aiogram.exceptions import TelegramNetworkError, TelegramServerError

logger = logging.getLogger(__name__)

STARTUP_RETRY_DELAYS_SECONDS = (0.5, 1.0, 2.0)
_TRANSIENT_TELEGRAM_ERRORS = (TelegramNetworkError, TelegramServerError)


async def retry_transient_telegram[T](
    operation: Callable[[], Awaitable[T]],
    *,
    operation_name: str,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    for attempt, delay in enumerate(STARTUP_RETRY_DELAYS_SECONDS, start=1):
        try:
            return await operation()
        except _TRANSIENT_TELEGRAM_ERRORS:
            logger.warning(
                "Transient Telegram failure during %s; retry %s/%s in %.1fs",
                operation_name,
                attempt,
                len(STARTUP_RETRY_DELAYS_SECONDS),
                delay,
                exc_info=True,
            )
            await sleep(delay)

    return await operation()
