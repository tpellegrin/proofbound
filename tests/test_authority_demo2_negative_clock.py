"""Regressions for the post-run adjudication of `pb-authority-demo-2`'s negative-clock claim.

Three separate things were conflated when the run reported that check, and each gets a case here:

* the **private witness is defective** at the state the run reported — directly reproducible, and
  true whether or not a conforming delay exists there;
* **search exhaustion is not nonexistence** — the run's post-hoc check walks 4,096 floats and its
  caller reads running out as proof. A constructed state shows it returning "none found" where a
  conforming delay exists;
* **nonexistence needs the whole domain covered**, and the final reflection's slope argument does
  not cover it. A concrete monotone admission predicate exhibits the gap: the least admitting delay
  breaks the bound and a larger one satisfies it, because `ulp` doubles at a power of two.

The historical artifacts are untouched; these test the dated adjudication added beside them.
"""
from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo" / "pb-authority-demo-2"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adjudication = _load(DEMO / "negative_clock_adjudication.py", "pb_demo2_negative_clock_adjudication")


class WitnessDefectTest(unittest.TestCase):
    """The reported state, reproduced from the committed witness."""

    def test_the_witness_answers_a_finite_delay_far_outside_the_bound(self):
        report = adjudication.witness_report()
        self.assertTrue(math.isfinite(report["witness_answered"]))
        self.assertTrue(report["admits_at_reached_instant"],
                        "the delay does reach an admitting instant; the bound is what fails")
        self.assertGreater(report["excess_ulps"], adjudication.MAX_EXCESS_ULPS)
        self.assertAlmostEqual(report["excess_ulps"], 61.7963878675, places=6)

    def test_the_defect_does_not_depend_on_which_requirement_is_violated(self):
        """Either a conforming delay exists and requirement 1 is broken, or none does and 7 is."""
        report = adjudication.witness_report()
        self.assertIn(report["verdict_at_this_state"], ("exists", "none", "unknown"))
        self.assertIn("Either way the witness", report["defect"])


class SearchExhaustionTest(unittest.TestCase):
    """A finite walk that runs out has established nothing about what it did not reach."""

    def setUp(self) -> None:
        sys.path.insert(0, str(DEMO / "external-suite" / "witness"))
        self.addCleanup(sys.path.remove, str(DEMO / "external-suite" / "witness"))
        self.probe = _load(DEMO / "posthoc_negative_clock.py", "pb_demo2_posthoc_probe")

    def test_the_probe_reports_no_conforming_delay_where_one_exists(self):
        # A clock at 1e9 and a rate whose reciprocal is not representable there: the delay's own
        # granularity is ~1e-23 while the instant moves in steps of ~1.2e-7, so 4,096 steps cannot
        # shift the sum at all.
        capacity, admissions, base = 1, 1, 1e9
        rate = 1.0 / (1.0 + 3e-8)
        clock, guard = adjudication.drained(adjudication.fixture_rateguard(),
                                            capacity, rate, base, admissions)
        clock.now = clock.now + 1.0
        now = clock.now
        self.assertFalse(adjudication.admits_at(capacity, rate, base, admissions, now),
                         "the state must actually be refused for the question to arise")

        exhausted = self.probe.a_conforming_delay_exists(capacity, rate, base, admissions, now,
                                                         capacity - admissions)
        self.assertIsNone(exhausted, "the historical search is expected to run out here")

        verdict, facts = adjudication.decide(capacity, rate, base, admissions, now)
        self.assertEqual(verdict, "exists", facts)

        # Verify the certificate independently of the module that produced it.
        w = facts["certificate"]
        reached = now + w
        self.assertTrue(adjudication.admits_at(capacity, rate, base, admissions, reached))
        exact = adjudication.exact_target(capacity, rate, base, admissions) - F(now)
        self.assertLessEqual(F(w) - exact,
                             adjudication.MAX_EXCESS_ULPS * F(math.ulp(reached)))


class BandCrossingTest(unittest.TestCase):
    """Why `none` needs more than checking the least admitting delay."""

    def test_a_larger_delay_can_conform_where_the_least_admitting_one_cannot(self):
        """Concrete, with an admission predicate that is monotone in the instant.

        Admission at `x >= T` with `T` the float just below 2.0, observed from `now = 1.5`, with
        the exact requirement six units in the last place below `T`. The least admitting delay
        overshoots the four-unit allowance; a larger delay lands on 2.0, where the allowance is
        twice as wide, and conforms. "The least one failed, so they all fail" is therefore false.
        """
        unit = 2.0 ** -52
        now = 1.5
        threshold = math.nextafter(2.0, 0.0)              # 2 - unit
        d = F(threshold) - 6 * F(unit)                    # the exact instant required
        w_star = d - F(now)

        def admits(x: float) -> bool:
            return x >= threshold

        candidates = []
        w = math.nextafter(float(w_star), 0.0)
        for _ in range(64):
            x = now + w
            if admits(x):
                candidates.append((w, x, F(w) - w_star, adjudication.MAX_EXCESS_ULPS
                                   * F(math.ulp(x))))
            w = math.nextafter(w, math.inf)
        self.assertTrue(candidates, "the scan must reach admitting delays")

        least_w, least_x, least_excess, least_allowance = candidates[0]
        self.assertGreater(least_excess, least_allowance,
                           "the least admitting delay must break the bound for this to be the "
                           "interesting case")
        conforming = [c for c in candidates if c[2] <= c[3]]
        self.assertTrue(conforming, "a larger delay must conform, or there is no gap to show")
        self.assertEqual(conforming[0][1], 2.0,
                         "it conforms precisely by reaching the wider band at the power of two")
        self.assertGreater(conforming[0][0], least_w)

        self.assertFalse(adjudication.larger_delays_excluded(least_x, d),
                         "the adjudication must answer `unknown` in exactly this regime")

    def test_the_reported_state_is_excluded_and_reports_why(self):
        capacity, rate, base, admissions, step = adjudication.WITNESS_STATE
        clock, _guard = adjudication.drained(adjudication.fixture_rateguard(),
                                             capacity, rate, base, admissions)
        clock.now = clock.now + step
        verdict, facts = adjudication.decide(capacity, rate, base, admissions, clock.now)
        self.assertEqual(verdict, "none", facts)
        self.assertTrue(facts["holds_under_probe_zero_unit_convention"])
        self.assertLess(facts["reached_instant"], 0.0, "this is the negative-clock regime")


class ForwardOrderingTest(unittest.TestCase):
    """The finding needs the earlier instant to be the one with an answer."""

    def test_a_strictly_forward_pair_runs_from_a_finite_answer_to_none(self):
        found = adjudication.forward_pair(points=40)
        self.assertGreater(found["forward_exists_then_none"], 0, found)
        exhibit = found["exhibit"]
        self.assertTrue(exhibit["ordering_checked"])
        self.assertLess(exhibit["earlier"]["now"], exhibit["later"]["now"])
        self.assertEqual(exhibit["earlier"]["verdict"], "exists")
        self.assertEqual(exhibit["later"]["verdict"], "none")

    def test_the_reflections_own_exhibit_is_ordered_the_other_way(self):
        """Preserved as a fact about that report: its instants are presented backwards."""
        stated_earlier = -7.155009762133426          # the report calls this `now_A`
        stated_later = -7.155009862133427            # and this one "1e-7 later"
        self.assertGreater(stated_earlier, stated_later,
                           "the report's `now_B` is earlier than its `now_A`, not later")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
