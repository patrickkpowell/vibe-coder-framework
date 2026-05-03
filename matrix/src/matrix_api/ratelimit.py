from __future__ import annotations

import asyncio
import time


class TokenBucket:
    def __init__(self, rate: int, per_seconds: float = 60.0) -> None:
        self._rate = rate
        self._per = per_seconds
        self._tokens = float(rate)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self._rate, self._tokens + elapsed * (self._rate / self._per))
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def retry_after_seconds(self) -> float:
        if self._tokens >= 1.0:
            return 0.0
        return (1.0 - self._tokens) / (self._rate / self._per)


def parse_rate(rate_str: str) -> tuple[int, float]:
    """Parse '30/minute' into (30, 60.0)."""
    count_str, unit = rate_str.split("/", 1)
    count = int(count_str.strip())
    seconds = {"second": 1.0, "minute": 60.0, "hour": 3600.0}.get(unit.strip().lower(), 60.0)
    return count, seconds
