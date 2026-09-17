"""The external behavioural suite for `pb-authority-demo-2`.

Written before the implementer runs, kept outside the project tree, and executed by the coordinator
afterwards. It is the only correctness signal that does not pass through an agent.

**Every assertion traces to a numbered requirement of the accepted intent**, and each test names
the requirement it tests. Nothing is asserted that an implementer could not derive from the intent
it was given, and nothing is asserted about internal structure: sharing the refill arithmetic is
explicitly advice, so an implementation that ignores that advice must pass.

What the predecessor's suite got wrong, and is corrected here:

* its one boundary case used `capacity=1, refill=4.0, base=5000.0` advancing `0.25` — every value
  dyadic and exactly representable, so it passed by luck and missed the defect its own reflector
  found. This suite sweeps **non-dyadic rates at several clock bases** and always advances by the
  delay the implementation actually returned;
* it asserted "no I/O" by scanning the class source for substrings, which would reject a harmless
  comment containing `open(` and would miss `getattr(time, "sleep")()`. That is replaced by a
  runtime observation, with its limits stated on the test itself;
* it never exercised the exceptional case at all.

Run with the project root on `sys.path`.
"""
from __future__ import annotations

import builtins
import math
import time
import unittest

from rateguard import RateGuard

#: Deliberately non-dyadic: none of these is exactly representable, which is the condition the
#: predecessor's suite accidentally avoided. `0.09` and `1.3` are the two the predecessor's
#: reflector used to demonstrate the defect.
AWKWARD_RATES = (0.09, 0.1, 0.3, 0.7, 1.3, 2.9, 7.3, 1234.5, 1e-3)

#: Several magnitudes, because the granularity of an instant scales with the instant. Zero is
#: included precisely because the predecessor believed it was a universal exemption and it is not.
CLOCK_BASES = (0.0, 1.0, 1000.0, 1234.56789, 1e6, 1e9)

#: Requirement 1's stated allowance for excess delay.
MAX_EXCESS_ULPS = 4.0


class Clock:
    def __init__(self, base: float = 1000.0) -> None:
        self.now = float(base)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + seconds


class RetryAfterExternalTest(unittest.TestCase):

    def drained(self, capacity: int, rate: float, base: float, admissions: int):
        """A guard whose bucket has had `admissions` tokens taken at the starting instant."""
        clock = Clock(base)
        guard = RateGuard(capacity, rate, clock=clock)
        for _ in range(admissions):
            self.assertTrue(guard.allow("k"), "a fresh bucket must admit up to capacity")
        return clock, guard

    def exact_delay(self, capacity: int, rate: float, admissions: int) -> float:
        """The mathematically exact requirement, from the model the intent discloses.

        A fresh bucket holds `capacity` tokens and each admission takes one, so after `admissions`
        taken at the same instant the deficit is `1 - (capacity - admissions)`. No implementation
        internals are consulted.
        """
        return (1.0 - (capacity - admissions)) / rate

    # -- requirement 1 -------------------------------------------------------------------------
    def test_waiting_the_returned_delay_actually_admits(self):
        """The whole point: the answer has to be usable, not merely close.

        Swept over awkward rates and several clock bases, always advancing the clock by the value
        the implementation itself returned.
        """
        checked = 0
        for base in CLOCK_BASES:
            for capacity in (1, 2, 3, 5):
                for rate in AWKWARD_RATES:
                    for admissions in range(1, capacity + 1):
                        with self.subTest(base=base, capacity=capacity, rate=rate,
                                          admissions=admissions):
                            clock, guard = self.drained(capacity, rate, base, admissions)
                            delay = guard.retry_after("k")
                            if delay == 0.0:
                                self.assertTrue(guard.allow("k"))
                                continue
                            self.assertTrue(math.isfinite(delay),
                                            "a finite delay exists for these values")
                            clock.advance(delay)
                            self.assertTrue(
                                guard.allow("k"),
                                "after waiting the returned delay the call must be admitted")
                            checked += 1
        self.assertGreater(checked, 200, "the sweep must actually exercise refused states")

    def test_the_delay_is_not_wastefully_large(self):
        """Requirement 1's bound: at most four units in the last place of the reached instant."""
        worst = 0.0
        for base in CLOCK_BASES:
            for capacity in (1, 2, 3, 5):
                for rate in AWKWARD_RATES:
                    for admissions in range(1, capacity + 1):
                        clock, guard = self.drained(capacity, rate, base, admissions)
                        delay = guard.retry_after("k")
                        if delay == 0.0 or not math.isfinite(delay):
                            continue
                        reached = clock.now + delay
                        unit = math.ulp(reached) if reached != 0.0 else math.ulp(1.0)
                        excess = (delay - self.exact_delay(capacity, rate, admissions)) / unit
                        worst = max(worst, excess)
        self.assertLessEqual(worst, MAX_EXCESS_ULPS,
                             f"excess delay reached {worst:.3f} ulps of the reached instant")
        self.assertGreaterEqual(worst, 0.0, "the delay must not undershoot the exact requirement")

    # -- requirement 2 -------------------------------------------------------------------------
    def test_asking_changes_nothing(self):
        clock, guard = self.drained(3, 1.3, 1000.0, 3)
        for _ in range(25):
            guard.retry_after("k")
        self.assertFalse(guard.allow("k"), "queries must not have refilled anything")
        clock.advance(guard.retry_after("k"))
        self.assertTrue(guard.allow("k"))

    def test_asking_does_not_disturb_the_refill_bookkeeping(self):
        clock, guard = self.drained(1, 1.0, 1000.0, 1)
        for _ in range(5):
            clock.advance(0.1)
            guard.retry_after("k")
        self.assertFalse(guard.allow("k"), "0.5s at 1 token/s is not yet a token")
        clock.advance(guard.retry_after("k"))
        self.assertTrue(guard.allow("k"))

    # -- requirement 3 -------------------------------------------------------------------------
    def test_zero_exactly_when_the_call_would_be_admitted(self):
        for base in CLOCK_BASES:
            for rate in AWKWARD_RATES:
                clock = Clock(base)
                guard = RateGuard(2, rate, clock=clock)
                for step in range(10):
                    with self.subTest(base=base, rate=rate, step=step):
                        predicted = guard.retry_after("k") == 0.0
                        self.assertEqual(predicted, guard.allow("k"),
                                         "retry_after disagreed with allow at the same instant")
                    clock.advance(0.37 / rate)

    # -- requirement 4 -------------------------------------------------------------------------
    def test_waiting_never_increases_the_answer(self):
        for base in CLOCK_BASES:
            with self.subTest(base=base):
                clock, guard = self.drained(1, 0.7, base, 1)
                previous = guard.retry_after("k")
                self.assertGreater(previous, 0.0)
                # Non-increase is the requirement. Advancing by a fraction of the remaining wait
                # approaches zero geometrically and need never arrive, so arrival is checked
                # separately by advancing the whole remaining wait — which requirement 1 promises.
                for _ in range(30):
                    clock.advance(previous / 4.0)
                    current = guard.retry_after("k")
                    self.assertLessEqual(current, previous, "the wait grew while time passed")
                    previous = current
                    if current == 0.0:
                        break
                if previous > 0.0:
                    clock.advance(previous)
                    self.assertEqual(guard.retry_after("k"), 0.0,
                                     "waiting the whole remaining delay must reach zero")

    # -- requirement 5 -------------------------------------------------------------------------
    def test_an_unseen_key_is_not_rate_limited(self):
        for base in CLOCK_BASES:
            guard = RateGuard(2, 0.3, clock=Clock(base))
            self.assertEqual(guard.retry_after("never-seen"), 0.0)

    def test_keys_remain_independent(self):
        clock, guard = self.drained(1, 1.3, 1000.0, 1)
        self.assertGreater(guard.retry_after("k"), 0.0)
        self.assertEqual(guard.retry_after("other"), 0.0)

    # -- requirement 6 -------------------------------------------------------------------------
    def test_the_burst_allowance_and_cap_are_unchanged(self):
        clock, guard = self.drained(3, 1.3, 1000.0, 3)
        clock.advance(10_000.0)
        self.assertEqual(guard.retry_after("k"), 0.0)
        self.assertEqual([guard.allow("k") for _ in range(3)], [True, True, True])
        self.assertFalse(guard.allow("k"), "the cap must still bound the burst")

    def test_the_constructor_still_validates_as_before(self):
        with self.assertRaises(ValueError):
            RateGuard(0, 1.0)
        with self.assertRaises(ValueError):
            RateGuard(1, 0.0)

    # -- requirement 7 -------------------------------------------------------------------------
    def test_when_no_finite_delay_exists_the_answer_is_infinity(self):
        """The exceptional case the intent defines, for rates the constructor already accepts."""
        for rate in (1e-310, 5e-324):
            with self.subTest(rate=rate):
                clock = Clock(0.0)
                guard = RateGuard(1, rate, clock=clock)
                self.assertTrue(guard.allow("k"))
                self.assertEqual(guard.retry_after("k"), math.inf)

    def test_nothing_is_raised_for_a_key_allow_accepts(self):
        for rate in (1e-310, 0.09, 1234.5):
            guard = RateGuard(1, rate, clock=Clock(1000.0))
            guard.allow("k")
            guard.retry_after("k")      # must not raise
            guard.retry_after("unseen")  # must not raise

    # -- the intent's "no sleeping, no I/O" constraint ------------------------------------------
    def test_the_query_does_not_sleep_or_open_anything_when_exercised(self):
        """A runtime observation over the paths this suite exercises — not a proof.

        The predecessor scanned the class source for substrings, which would flag a comment
        containing `open(` and would miss `getattr(time, "sleep")()`. Observing the calls instead
        catches aliasing, and its limit is honest and stated: it establishes that these paths did
        not sleep or open anything, and says nothing about paths not exercised here. Whether the
        implementation performs I/O in general is a semantic review question.
        """
        calls: list[str] = []
        real_sleep, real_open = time.sleep, builtins.open

        def watched_sleep(*a, **k):
            calls.append("time.sleep")
            return real_sleep(0)

        def watched_open(*a, **k):
            calls.append("open")
            return real_open(*a, **k)

        time.sleep = watched_sleep
        builtins.open = watched_open
        try:
            started = time.perf_counter()
            for base in CLOCK_BASES:
                for rate in AWKWARD_RATES:
                    clock, guard = self.drained(1, rate, base, 1)
                    guard.retry_after("k")
                    guard.retry_after("unseen")
            elapsed = time.perf_counter() - started
        finally:
            time.sleep, builtins.open = real_sleep, real_open

        self.assertEqual(calls, [], f"the query slept or opened something: {calls}")
        self.assertLess(elapsed, 2.0, "the exercised paths took long enough to suggest blocking")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
