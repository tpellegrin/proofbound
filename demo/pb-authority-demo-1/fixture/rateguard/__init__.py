"""A token-bucket rate limiter.

One bucket per key. A bucket starts full, loses a token per admitted call, and refills at a
constant rate up to its capacity. The clock is injectable so behaviour is testable without
sleeping.
"""
from __future__ import annotations

import time
from typing import Callable, Dict


class RateGuard:
    """Admit or refuse calls per key, at a bounded long-run rate with a burst allowance."""

    def __init__(self, capacity: int, refill_per_second: float, *,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        if refill_per_second <= 0:
            raise ValueError("refill_per_second must be positive")
        self.capacity = int(capacity)
        self.refill_per_second = float(refill_per_second)
        self._clock = clock
        self._tokens: Dict[str, float] = {}
        self._last: Dict[str, float] = {}

    def allow(self, key: str) -> bool:
        """Whether this call is admitted, consuming a token when it is.

        A key never seen before starts with a full bucket.
        """
        now = self._clock()
        tokens = self._tokens.get(key, float(self.capacity))
        last = self._last.get(key, now)
        elapsed = now - last
        if elapsed < 0.0:
            elapsed = 0.0
        tokens = tokens + elapsed * self.refill_per_second
        if tokens > self.capacity:
            tokens = float(self.capacity)
        self._last[key] = now
        if tokens >= 1.0:
            self._tokens[key] = tokens - 1.0
            return True
        self._tokens[key] = tokens
        return False
