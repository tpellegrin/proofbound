"""Private witness implementation, for establishing that the external suite is satisfiable.

**Never placed in the demonstration project and never shown to any worker.** It exists so the
coordinator can establish, before paying for an implementer, that the suite's assertions are
mutually consistent and achievable. An unsatisfiable suite would make the demonstration meaningless
whatever the implementer did.

It happens to take the intent's advice and share the refill arithmetic. That is one acceptable
shape, not the required one.

The interesting part is `retry_after`, which searches in **instant** space rather than delay space.
The mathematically exact delay is the starting point, not the answer: adding it to the clock may
land on an instant that still refuses, and a strictly larger delay can produce the very same
instant. So the search advances the achieved instant and reports the delay that reaches it.
"""
from __future__ import annotations

import math
import time
from typing import Callable, Dict

#: How many instants to walk before giving up. The correction needed is a couple of units in the
#: last place; this is slack, not a tuning parameter.
_MAX_STEPS = 256


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
        """Seconds to wait so that advancing the clock by the result admits. Changes nothing."""
        now = self._clock()
        available = self._available(key, now)
        if available >= 1.0:
            return 0.0

        wait = (1.0 - available) / self.refill_per_second
        if not math.isfinite(wait):
            return math.inf

        for _ in range(_MAX_STEPS):
            reached = now + wait
            if not math.isfinite(reached):
                return math.inf
            if self._available(key, reached) >= 1.0:
                return wait
            # Move the *instant* on, then report the delay that reaches it. When the delay's own
            # granularity is too coarse to shift the sum, nudge the delay instead — otherwise the
            # search would sit still while believing it had advanced.
            nudged = nextafter_delay(now, reached, wait)
            if nudged is None:
                return math.inf
            wait = nudged
        return math.inf


def nextafter_delay(now: float, reached: float, wait: float) -> "float | None":
    """The smallest delay larger than `wait` that could reach a later instant than `reached`."""
    target = math.nextafter(reached, math.inf)
    if not math.isfinite(target):
        return None
    candidate = target - now
    if math.isfinite(candidate) and candidate > wait:
        return candidate
    candidate = math.nextafter(wait, math.inf)
    if math.isfinite(candidate) and candidate > wait:
        return candidate
    return None
