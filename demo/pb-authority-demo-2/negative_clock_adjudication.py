#!/usr/bin/env python3
"""**Dated addition, 2026-09-17, after `pb-authority-demo-2` stopped.** Not part of the run.

The run's own records are unmodified, including `posthoc_negative_clock.py`, whose output the run
report quotes. This file exists because that check's central inference does not hold in general,
and the claim it supported deserves either a real argument or a narrower statement.

## What was wrong with the inference

`posthoc_negative_clock.a_conforming_delay_exists` walks at most 4,096 successive floats upward
from the exact deficit and returns `None` when it runs out. Its caller reads `None` as *no finite
delay can satisfy requirement 1*. A finite search establishes nonexistence only if its completeness
is argued, and nothing argued it. The gap is reproducible: with `capacity=1`, an unrepresentable
rate and a clock at `1e9`, the search exhausts while a conforming delay exists 0.248 units in the
last place above the exact requirement — a correct implementation would be reported as defective.
The reviewer's own scripts, retained outside the repository under the executor's scratch directory,
classify states the same way and justify it with a slope argument that ignores what `ulp` does at a
power of two.

## What replaces it

A three-valued decision — `exists`, `none`, `unknown` — where `none` is returned only when an
argument covers every larger delay. Three facts do the work, for a bucket drained at `base` and
observed at `now`, with `d` the exact instant the bucket reaches one token:

1. **Admission is monotone in the instant.** `allow` computes
   `tokens + max(0, x - last) * rate >= 1` in IEEE-754 binary64 with round-to-nearest, and each of
   those operations is non-decreasing in `x`. So is `x = now + w` in `w`. The admitting delays are
   therefore an up-set, the least admitting delay `w0` is well defined, and it is found by
   bisection over bit patterns rather than by stepping — the predecessor's search never looked
   *below* the exact deficit, where a delay may admit with negative excess and conform trivially.
2. **Excess grows while the allowance does not, inside one binary exponent.** Excess
   `e(w) = w - w*` is strictly increasing. For `x(w)` no larger in magnitude than `x(w0)`,
   `4*ulp(x(w))` cannot exceed `4*ulp(x(w0))`. So if `w0` already exceeds its allowance, no `w`
   whose instant stays in that band can conform.
3. **Crossing into a wider band costs more than the band gains.** The only way `ulp` grows is for
   the instant to reach `P`, the next power of two above `|x(w0)|`. Reaching `P` forces
   `e >= P - 2**(E-54) - d`, while the allowance there is at most `2**-50 * (d + e)` — so where
   that lower bound on the excess already exceeds that upper bound on the allowance, nothing above
   `P` conforms either. When it does not, the answer is `unknown`, not `none`: this is the regime
   where a delay whose instant lands exactly on a power of two genuinely can be rescued, and
   `tests/test_authority_demo2_negative_clock.py` exhibits a monotone predicate where it is.

`allow`'s arithmetic is the fixture's, loaded by path rather than from `PYTHONPATH`, because intent
requirement 6 fixes it: an implementation may not change what `allow` admits.

## What it establishes, and what stays a reading

At the witness state the run reported, `none` holds under this argument, so the witness's finite
answer is a defect either way — it violates requirement 1's bound if a conforming delay exists and
requirement 7 if none does. At the reviewer's configuration a **strictly forward** scan finds
states where a conforming delay exists and a *later* one where none does, which is the shape the
intent-defect finding needs and which the reviewer's own decisive exhibit did not have: its two
instants were presented in the wrong order.

Two readings are doing real work and neither is mechanical. *"The mathematically exact
requirement"* is read as the real-arithmetic deficit, as the intent's own worked examples use it.
Requirement 1 is read as requiring a **finite** delay wherever a conforming one exists; under a
literal extended-real reading `math.inf` satisfies its text, which would make "always infinity" a
conforming answer and defeat the requirement's stated purpose. That is itself an intent defect, and
it is a semantic judgement rather than something this file computes.

    python3 demo/pb-authority-demo-2/negative_clock_adjudication.py witness
    python3 demo/pb-authority-demo-2/negative_clock_adjudication.py pair [--points N]
    python3 demo/pb-authority-demo-2/negative_clock_adjudication.py replay-probe
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import struct
import sys
from fractions import Fraction as F
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent

#: The state the run's post-hoc check reported as a failure: capacity, refill, clock base,
#: admissions, and the advance applied afterwards.
WITNESS_STATE = (2, 0.5189678343212376, -1.9412437153089475, 2, 0.9221153803261514)

#: The configuration the final specification reflection reasoned about.
REVIEWER_STATE = (2, 0.10978710655568508, -7.155015362133442, 2)

MAX_EXCESS_ULPS = 4


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_rateguard() -> Any:
    """The fixture's limiter. Requirement 6 fixes `allow`, so admission is read from here."""
    return _load(HERE / "fixture" / "rateguard" / "__init__.py", "pb_demo2_fixture_rateguard")


def witness_rateguard() -> Any:
    return _load(HERE / "external-suite" / "witness" / "rateguard" / "__init__.py",
                 "pb_demo2_witness_rateguard")


class Clock:
    def __init__(self, t: float) -> None:
        self.now = float(t)

    def __call__(self) -> float:
        return self.now


def _bits(x: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", x))[0]


def _from_bits(n: int) -> float:
    return struct.unpack("<d", struct.pack("<Q", n))[0]


def drained(guard_module: Any, capacity: int, rate: float, base: float, admissions: int):
    """A bucket drained by `admissions` calls at `base`, using only the public API."""
    clock = Clock(base)
    guard = guard_module.RateGuard(capacity, rate, clock=clock)
    for _ in range(admissions):
        if not guard.allow("k"):
            raise ValueError("the state is not reachable: an admission was refused at base")
    return clock, guard


def admits_at(capacity: int, rate: float, base: float, admissions: int, x: float) -> bool:
    """Whether the fixture's `allow` admits at instant `x`, from the drained state."""
    module = _FIXTURE[0] or fixture_rateguard()
    _FIXTURE[0] = module
    clock, guard = drained(module, capacity, rate, base, admissions)
    clock.now = x
    return guard.allow("k")


_FIXTURE: "list[Any]" = [None]


def exact_target(capacity: int, rate: float, base: float, admissions: int) -> F:
    """The exact instant the bucket reaches one token, from the model the intent discloses."""
    return F(base) + (1 - F(capacity - admissions)) / F(rate)


def larger_delays_excluded(x0: float, d: F) -> bool:
    """Can a delay whose instant reaches a wider `ulp` band conform, when the least one cannot?

    `False` means it is not excluded, and the caller must answer `unknown` rather than `none`.
    This is the step the final reflection's slope argument skipped: excess does grow faster than
    the allowance *within* a binary exponent, but the allowance **doubles** at a power of two, and
    a delay whose instant lands just past one can conform where its predecessor could not.

    Reaching the next band at `P` forces the excess to at least `P - 2**(E-54) - d`, because
    rounding to nearest cannot deliver an instant of `P` or beyond from a smaller real sum. The
    allowance anywhere at or beyond `P` is at most `2**-50/(1 - 2**-53) * (d + excess)`, since
    `ulp(x) <= x * 2**-52` for normal `x`. Where the first exceeds the second, nothing past `P`
    conforms.
    """
    _, exponent = math.frexp(x0)
    next_band = F(2) ** exponent                       # |x| must reach this for ulp to grow
    floor_excess = next_band - F(2) ** (exponent - 54) - d
    slack = F(2) ** -50 / (1 - F(2) ** -53)
    return bool(floor_excess > 0 and floor_excess * (1 - slack) > slack * d)


def decide(capacity: int, rate: float, base: float, admissions: int,
           now: float) -> "tuple[str, dict[str, Any]]":
    """Does a finite delay satisfying requirement 1 exist at `now`? `exists` / `none` / `unknown`.

    `zero` reports the state that is not refused at all, where requirement 1 asks for `0.0`.
    """
    if admits_at(capacity, rate, base, admissions, now):
        return "zero", {"why": "the call is admitted at this instant"}
    d = exact_target(capacity, rate, base, admissions)
    w_star = d - F(now)

    def reaches(w: float) -> bool:
        x = now + w
        return math.isfinite(x) and admits_at(capacity, rate, base, admissions, x)

    hi = max(float(w_star), 5e-324)
    while not reaches(hi):
        nxt = hi * 2.0
        if not math.isfinite(nxt) or not math.isfinite(now + nxt):
            return "none", {"why": "no finite delay reaches an admitting instant at all",
                            "clause": "a"}
        hi = nxt
    low, high = _bits(0.0), _bits(hi)        # w == 0.0 reaches `now`, which refuses
    while high - low > 1:
        mid = (low + high) // 2
        if reaches(_from_bits(mid)):
            high = mid
        else:
            low = mid
    w0 = _from_bits(high)
    if not reaches(w0) or reaches(math.nextafter(w0, 0.0)):   # monotonicity, checked not assumed
        return "unknown", {"why": "admission is not the up-set the argument requires"}

    x0 = now + w0
    excess = F(w0) - w_star
    allowance = MAX_EXCESS_ULPS * F(math.ulp(x0))
    facts: "dict[str, Any]" = {
        "least_admitting_delay": w0, "reached_instant": x0,
        "excess_ulps": float(excess / F(math.ulp(x0))), "exact_target_instant": float(d)}
    if excess <= allowance:
        return "exists", {**facts, "certificate": w0}

    # Nonexistence needs every larger delay covered. Facts 2 and 3 of the module docstring.
    if x0 == 0.0 or abs(x0) < 2.0 ** -1022:
        return "unknown", {**facts, "why": "the least admitting instant is zero or subnormal"}
    if not larger_delays_excluded(x0, d):
        return "unknown", {**facts, "why": "a delay reaching the next binary exponent is not "
                                           "excluded; it may conform there"}
    facts["next_band"] = float(F(2) ** math.frexp(x0)[1])
    facts["holds_under_probe_zero_unit_convention"] = bool(
        x0 > 0 or -d - F(2) ** -1075 > MAX_EXCESS_ULPS * F(math.ulp(1.0)))
    return "none", facts


def witness_report() -> "dict[str, Any]":
    """What the private witness answers at the reported state, and what is true there."""
    capacity, rate, base, admissions, step = WITNESS_STATE
    clock, guard = drained(witness_rateguard(), capacity, rate, base, admissions)
    clock.now = clock.now + step                 # only the injected clock moves; the guard is not touched
    now = clock.now
    answered = guard.retry_after("k")
    d = exact_target(capacity, rate, base, admissions)
    verdict, facts = decide(capacity, rate, base, admissions, now)
    report = {"state": {"capacity": capacity, "refill_per_second": rate, "clock_base": base,
                        "admissions": admissions, "advance": step, "now": now},
              "witness_answered": answered,
              "verdict_at_this_state": verdict, "facts": facts}
    if math.isfinite(answered) and answered > 0:
        reached = now + answered
        report["reached_instant"] = reached
        report["admits_at_reached_instant"] = admits_at(capacity, rate, base, admissions, reached)
        report["excess_ulps"] = float((F(answered) - (d - F(now))) / F(math.ulp(reached)))
        report["defect"] = (
            "the witness returns a finite delay whose excess is above four units in the last "
            "place of the instant it reaches. If a conforming delay exists this violates "
            "requirement 1; if none does, requirement 7 demands math.inf. Either way the witness "
            "is wrong here, independently of which it is.")
    return report


def forward_pair(points: int = 1200, step: float = 1e-7) -> "dict[str, Any]":
    """Scan strictly forward in time and report exists-then-none pairs.

    Requirement 4 forbids the answer increasing as the clock advances. A state where a conforming
    finite delay exists, followed by a *later* one where none does, forces exactly that increase
    under the reading in this module's docstring.
    """
    capacity, rate, base, admissions = REVIEWER_STATE
    seen: "list[tuple[float, str]]" = []
    counts: "dict[str, int]" = {}
    now = base
    for _ in range(points):
        now = now + step
        verdict, _facts = decide(capacity, rate, base, admissions, now)
        counts[verdict] = counts.get(verdict, 0) + 1
        seen.append((now, verdict))
    pairs = [(a, b) for (a, va), (b, vb) in zip(seen, seen[1:])
             if va == "exists" and vb == "none"]
    out: "dict[str, Any]" = {"state": {"capacity": capacity, "refill_per_second": rate,
                                       "clock_base": base, "admissions": admissions},
                             "points": points, "step": step, "verdicts": counts,
                             "forward_exists_then_none": len(pairs)}
    if pairs:
        earlier, later = pairs[0]
        ev, ef = decide(capacity, rate, base, admissions, earlier)
        lv, lf = decide(capacity, rate, base, admissions, later)
        out["exhibit"] = {
            "earlier": {"now": earlier, "verdict": ev, **ef},
            "later": {"now": later, "verdict": lv, **lf},
            "ordering_checked": earlier < later,
            "means": "with no intervening calls, a conforming finite delay exists at the earlier "
                     "instant and none exists at the later one, so any answer satisfying "
                     "requirements 1 and 7 increases from finite to math.inf, which requirement 4 "
                     "forbids"}
    return out


def replay_probe() -> "dict[str, Any]":
    """Re-adjudicate the seeded cases the run's post-hoc check actually walked."""
    # The run invoked the probe against the private witness, so the replay resolves `rateguard`
    # the same way. Admission for the *decision* still comes from the fixture, via `admits_at`.
    sys.path.insert(0, str(HERE / "external-suite" / "witness"))
    sys.path.insert(0, str(HERE))
    import posthoc_negative_clock as probe                         # noqa: E402

    import random
    random.seed(20260917)
    cases = [WITNESS_STATE]
    for _ in range(400):
        capacity = random.choice((1, 2, 3))
        rate = math.exp(random.uniform(math.log(1e-3), math.log(10.0)))
        base = -random.uniform(0.5, 4.0)
        admissions = random.randint(1, capacity)
        step = random.uniform(0.0, 2.0)
        cases.append((capacity, rate, base, admissions, step))

    module = witness_rateguard()
    tally: "dict[str, int]" = {}
    disagreements = []
    for capacity, rate, base, admissions, step in cases:
        try:
            clock, guard = drained(module, capacity, rate, base, admissions)
        except ValueError:
            continue
        clock.now = clock.now + step
        now = clock.now
        if guard.retry_after("k") == 0.0:
            continue
        searched = probe.a_conforming_delay_exists(capacity, rate, base, admissions, now,
                                                   capacity - admissions)
        verdict, facts = decide(capacity, rate, base, admissions, now)
        key = f"search={'found' if searched is not None else 'exhausted'} decision={verdict}"
        tally[key] = tally.get(key, 0) + 1
        if searched is None and verdict != "none":
            disagreements.append({"state": [capacity, rate, base, admissions, step],
                                  "verdict": verdict, "facts": facts})
    return {"cases_adjudicated": sum(tally.values()), "tally": tally,
            "search_exhausted_but_not_established": disagreements[:4],
            "note": "agreement here is a fact about these seeded cases, not about the "
                    "inference: exhaustion still does not establish nonexistence in general"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Adjudicate the negative-clock claim.")
    parser.add_argument("command", choices=["witness", "pair", "replay-probe"])
    parser.add_argument("--points", type=int, default=1200)
    args = parser.parse_args()
    table = {"witness": witness_report,
             "pair": lambda: forward_pair(points=args.points),
             "replay-probe": replay_probe}
    print(json.dumps(table[args.command](), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
