"""The external behavioural suite for `pb-authority-demo-1`.

Written before the implementer runs, kept outside the project tree, and executed by the
orchestrator afterwards. It is the only correctness signal that does not pass through an agent.

**Every assertion here traces to a numbered point of the accepted intent**, and the point is named
in each test. Nothing is asserted that an implementer could not have derived from the intent it was
given, and nothing is asserted about internal structure: how the refill arithmetic is factored is
explicitly advice in the intent, so an implementation that ignores that advice must still pass.

Run with the project root on `sys.path`:

    PYTHONPATH=<project> python3 -m unittest discover -s external-suite -t external-suite
"""
from __future__ import annotations

import inspect
import unittest

from rateguard import RateGuard


class FakeClock:
    def __init__(self) -> None:
        self.now = 5000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RetryAfterExternalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()

    def guard(self, capacity: int = 2, refill_per_second: float = 1.0) -> RateGuard:
        return RateGuard(capacity, refill_per_second, clock=self.clock)

    # -- point 5 -------------------------------------------------------------------------------
    def test_an_unseen_key_is_not_rate_limited(self):
        self.assertEqual(self.guard().retry_after("never-seen"), 0.0)

    # -- point 1 -------------------------------------------------------------------------------
    def test_it_answers_zero_while_the_bucket_still_has_tokens(self):
        guard = self.guard(capacity=2)
        self.assertEqual(guard.retry_after("a"), 0.0)
        self.assertTrue(guard.allow("a"))
        self.assertEqual(guard.retry_after("a"), 0.0)

    def test_it_answers_the_time_until_one_token_has_refilled(self):
        guard = self.guard(capacity=1, refill_per_second=2.0)
        self.assertTrue(guard.allow("a"))
        # Empty bucket, 2 tokens per second: half a second until the next admission.
        self.assertAlmostEqual(guard.retry_after("a"), 0.5, places=6)

    # -- point 2 -------------------------------------------------------------------------------
    def test_asking_does_not_consume_a_token(self):
        guard = self.guard(capacity=3)
        for _ in range(10):
            guard.retry_after("a")
        self.assertEqual([guard.allow("a") for _ in range(3)], [True, True, True])
        self.assertFalse(guard.allow("a"))

    def test_asking_does_not_disturb_the_refill_clock(self):
        """Repeated queries across time must not reset or advance the bucket's own bookkeeping."""
        guard = self.guard(capacity=1, refill_per_second=1.0)
        self.assertTrue(guard.allow("a"))
        for _ in range(5):
            self.clock.advance(0.1)
            guard.retry_after("a")
        # 0.5 s elapsed at 1 token/s: not yet a full token, so still refused.
        self.assertFalse(guard.allow("a"))
        self.clock.advance(0.5)
        self.assertTrue(guard.allow("a"))

    # -- point 3 -------------------------------------------------------------------------------
    def test_zero_exactly_when_the_call_would_be_admitted(self):
        guard = self.guard(capacity=2, refill_per_second=1.0)
        for step in range(12):
            with self.subTest(step=step):
                predicted_admit = guard.retry_after("a") == 0.0
                self.assertEqual(predicted_admit, guard.allow("a"),
                                 "retry_after disagreed with allow at the same instant")
            self.clock.advance(0.4)

    # -- point 4 -------------------------------------------------------------------------------
    def test_waiting_never_increases_the_answer(self):
        guard = self.guard(capacity=1, refill_per_second=1.0)
        self.assertTrue(guard.allow("a"))
        previous = guard.retry_after("a")
        self.assertGreater(previous, 0.0)
        for _ in range(20):
            self.clock.advance(0.05)
            current = guard.retry_after("a")
            self.assertLessEqual(current, previous + 1e-9, "the wait grew while time passed")
            previous = current
        self.assertEqual(previous, 0.0, "the wait never reached zero")

    # -- point 6 and the boundary --------------------------------------------------------------
    def test_at_the_refill_boundary_it_is_zero_and_the_call_is_admitted(self):
        guard = self.guard(capacity=1, refill_per_second=4.0)
        self.assertTrue(guard.allow("a"))
        self.clock.advance(0.25)  # exactly one token
        self.assertEqual(guard.retry_after("a"), 0.0)
        self.assertTrue(guard.allow("a"))

    def test_the_burst_allowance_is_still_respected(self):
        guard = self.guard(capacity=3, refill_per_second=1.0)
        self.clock.advance(1000.0)
        self.assertEqual(guard.retry_after("a"), 0.0)
        self.assertEqual([guard.allow("a") for _ in range(3)], [True, True, True])
        self.assertFalse(guard.allow("a"))
        self.assertGreater(guard.retry_after("a"), 0.0)

    def test_keys_remain_independent(self):
        guard = self.guard(capacity=1, refill_per_second=1.0)
        self.assertTrue(guard.allow("a"))
        self.assertGreater(guard.retry_after("a"), 0.0)
        self.assertEqual(guard.retry_after("b"), 0.0)

    # -- the intent's "no I/O, no sleeping" constraint ------------------------------------------
    def test_the_query_neither_sleeps_nor_performs_io(self):
        source = inspect.getsource(RateGuard)
        for forbidden in ("time.sleep", "open(", "socket", "requests", "urllib", "subprocess"):
            self.assertNotIn(forbidden, source,
                             f"the limiter must not {forbidden!r}; the intent forbids I/O and sleeping")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
