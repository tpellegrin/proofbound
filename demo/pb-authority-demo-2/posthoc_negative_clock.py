#!/usr/bin/env python3
"""A post-hoc check the frozen external suite cannot make. Reported separately, never merged.

The frozen suite's clock bases are all non-negative. That was a deliberate choice about the
predecessor's dyadic blind spot and it was fixed before any worker ran, which is the only reason its
verdict is worth anything — so it is not being edited now. But neither the accepted intent nor the
specification restricts the injected clock's domain, and a negative clock reaches states the suite
cannot see: when the reached instant crosses zero, `ulp(x)` collapses, so a rounding error far below
one unit in the last place of the *delay* becomes tens of units in the last place of the *instant*.

In such a state no finite delay can satisfy the intent's requirement 1, and requirement 7 then
requires `math.inf`. This check verifies exactly that correspondence, from the model the intent
discloses, against whatever implementation is on `PYTHONPATH`. Its verdict is reported on its own
terms and is never combined with the frozen suite's.

    PYTHONPATH=<project> python3 demo/pb-authority-demo-2/posthoc_negative_clock.py
"""
from __future__ import annotations

import json
import math
import random
import sys
from fractions import Fraction as F

from rateguard import RateGuard

MAX_EXCESS_ULPS = 4.0

#: How far above the smallest admitting delay to keep looking for one that also meets the bound.
#: Excess grows one-for-one with the delay while `4*ulp(x)` grows by a factor of about 2**-50 of it,
#: so a delay that overshoots the bound cannot be rescued by growing — but the search is run anyway
#: rather than asserted, because the reached instant's exponent does change as it moves.
SEARCH_STEPS = 4096


class Clock:
    def __init__(self, t: float) -> None:
        self.now = float(t)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + seconds


def drained(capacity: int, rate: float, base: float, admissions: int, step: float):
    """A guard drained at `base`, then observed `step` later. Only the public API is used."""
    clock = Clock(base)
    guard = RateGuard(capacity, rate, clock=clock)
    for _ in range(admissions):
        if not guard.allow("k"):
            return None
    clock.advance(step)
    return clock, guard


def exact_deficit_delay(capacity: int, rate: float, base: float, admissions: int,
                        now: float) -> F:
    """The exact real delay, from the disclosed model: bucket drained at `base`, none since.

    `admissions` tokens were taken at `base`, so the token count there is `capacity - admissions`,
    and it refills at `rate`. No implementation internals are read.
    """
    tokens = F(capacity - admissions)
    target = F(base) + (F(1) - tokens) / F(rate)
    return target - F(now)


def a_conforming_delay_exists(capacity: int, rate: float, base: float, admissions: int,
                              now: float, tokens_at_base: int) -> "float | None":
    """The smallest finite delay that both admits and stays inside the four-ulp bound, if any."""
    w_star = exact_deficit_delay(capacity, rate, base, admissions, now)
    w = float(w_star)
    if w <= 0.0:
        w = math.ulp(0.0)
    for _ in range(SEARCH_STEPS):
        x = now + w
        if not math.isfinite(x):
            return None
        # Rebuild the same bucket state at `base` and ask at `x`, using only the public API: the
        # clock is ours, so it is moved rather than the guard being reached into.
        probe_clock = Clock(base)
        probe = RateGuard(capacity, rate, clock=probe_clock)
        for _ in range(admissions):
            probe.allow("k")
        probe_clock.now = x
        if probe.allow("k"):
            unit = math.ulp(x) if x != 0.0 else math.ulp(1.0)
            if (F(w) - w_star) <= F(MAX_EXCESS_ULPS) * F(unit):
                return w
        w = math.nextafter(w, math.inf)
    return None


def main() -> int:
    random.seed(20260917)
    checked = inf_cases = finite_cases = 0
    failures = []

    cases = [(2, 0.5189678343212376, -1.9412437153089475, 2, 0.9221153803261514)]
    for _ in range(400):
        capacity = random.choice((1, 2, 3))
        rate = math.exp(random.uniform(math.log(1e-3), math.log(10.0)))
        base = -random.uniform(0.5, 4.0)
        admissions = random.randint(1, capacity)
        step = random.uniform(0.0, 2.0)
        cases.append((capacity, rate, base, admissions, step))

    for capacity, rate, base, admissions, step in cases:
        made = drained(capacity, rate, base, admissions, step)
        if made is None:
            continue
        clock, guard = made
        now = clock.now
        answered = guard.retry_after("k")
        if answered == 0.0:
            continue
        checked += 1
        conforming = a_conforming_delay_exists(capacity, rate, base, admissions, now,
                                               capacity - admissions)
        if math.isinf(answered):
            inf_cases += 1
            if conforming is not None:
                failures.append({"why": "answered infinity while a conforming finite delay exists",
                                 "capacity": capacity, "rate": rate, "base": base,
                                 "admissions": admissions, "step": step,
                                 "conforming": conforming})
            continue
        finite_cases += 1
        if conforming is None:
            failures.append({"why": "answered a finite delay where none can satisfy requirement 1",
                             "capacity": capacity, "rate": rate, "base": base,
                             "admissions": admissions, "step": step, "answered": answered})
            continue
        clock.advance(answered)
        if not guard.allow("k"):
            failures.append({"why": "the returned delay did not admit", "answered": answered,
                             "capacity": capacity, "rate": rate, "base": base})
            continue
        x = now + answered
        unit = math.ulp(x) if x != 0.0 else math.ulp(1.0)
        excess = float(F(answered) - exact_deficit_delay(capacity, rate, base, admissions, now))
        if excess / unit > MAX_EXCESS_ULPS:
            failures.append({"why": "excess above the four-ulp bound",
                             "ulps": excess / unit, "capacity": capacity, "rate": rate,
                             "base": base, "answered": answered})

    print(json.dumps({"kind": "post-hoc negative-clock check, not part of the frozen suite",
                      "refused_states_checked": checked,
                      "answered_infinity": inf_cases,
                      "answered_finite": finite_cases,
                      "failures": failures[:8],
                      "failure_count": len(failures)}, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
