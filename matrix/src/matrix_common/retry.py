from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retriable: tuple[type[Exception], ...] = (Exception,),
) -> T:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await fn()
        except retriable as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                delay = min(base_delay * (2**attempt), max_delay)
                logger.warning(
                    "Attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt + 1,
                    max_attempts,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]
