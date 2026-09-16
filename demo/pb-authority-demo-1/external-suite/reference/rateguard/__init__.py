"""Reference implementation, for proving the external suite is satisfiable.

**Never placed in the demonstration project and never shown to any worker.** It exists so the
orchestrator can establish, before paying for an implementer, that the external suite's assertions
are mutually consistent and achievable — an unsatisfiable suite would make the demonstration
meaningless whatever the implementer did.

It happens to take the intent's advice and share the refill arithmetic. That is one acceptable
shape, not the required one.
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

    def _available(self, key: str, now: float) -> float:
        """Tokens this key would have at `now`, computed without changing anything."""
        tokens = self._tokens.get(key, float(self.capacity))
        last = self._last.get(key, now)
        elapsed = now - last
        if elapsed < 0.0:
            elapsed = 0.0
        tokens = tokens + elapsed * self.refill_per_second
        if tokens > self.capacity:
            tokens = float(self.capacity)
        return tokens

    def allow(self, key: str) -> bool:
        """Whether this call is admitted, consuming a token when it is."""
        now = self._clock()
        tokens = self._available(key, now)
        self._last[key] = now
        if tokens >= 1.0:
            self._tokens[key] = tokens - 1.0
            return True
        self._tokens[key] = tokens
        return False

    def retry_after(self, key: str) -> float:
        """Seconds until `allow(key)` would admit; `0.0` if it would admit now. Changes nothing."""
        tokens = self._available(key, self._clock())
        if tokens >= 1.0:
            return 0.0
        return (1.0 - tokens) / self.refill_per_second
