"""The project's own suite. It must keep passing, unedited, across the accepted change."""
from __future__ import annotations

import unittest

from rateguard import RateGuard


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RateGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()

    def guard(self, capacity: int = 3, refill_per_second: float = 1.0) -> RateGuard:
        return RateGuard(capacity, refill_per_second, clock=self.clock)

    def test_a_fresh_key_may_burst_to_capacity_then_is_refused(self):
        guard = self.guard(capacity=3)
        self.assertEqual([guard.allow("a") for _ in range(3)], [True, True, True])
        self.assertFalse(guard.allow("a"))

    def test_waiting_refills_one_token_per_period(self):
        guard = self.guard(capacity=2, refill_per_second=2.0)
        self.assertTrue(guard.allow("a"))
        self.assertTrue(guard.allow("a"))
        self.assertFalse(guard.allow("a"))
        self.clock.advance(0.5)
        self.assertTrue(guard.allow("a"))

    def test_a_bucket_never_refills_past_capacity(self):
        guard = self.guard(capacity=2)
        self.assertTrue(guard.allow("a"))
        self.clock.advance(1000.0)
        self.assertEqual([guard.allow("a") for _ in range(2)], [True, True])
        self.assertFalse(guard.allow("a"))

    def test_keys_are_independent(self):
        guard = self.guard(capacity=1)
        self.assertTrue(guard.allow("a"))
        self.assertFalse(guard.allow("a"))
        self.assertTrue(guard.allow("b"))

    def test_invalid_configuration_is_refused(self):
        with self.assertRaises(ValueError):
            RateGuard(0, 1.0)
        with self.assertRaises(ValueError):
            RateGuard(1, 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
