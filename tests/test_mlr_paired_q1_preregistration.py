#!/usr/bin/env python3
"""The frozen design of `mlr-deepseek-v4-flash-high-paired-q1`, checked against the machinery.

A preregistration is only worth the freeze if the runner actually implements it. These assert the
parts of the plan a later edit could silently break: the identity, the sample count, the exact slot
order, the arm exposure, the attribution version, the retry cap, and the guarantee that an invalid
attempt cannot present itself as a valid one. No provider call is made.
"""
from __future__ import annotations

import platform
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import _hermetic      # noqa: E402
import _mlr           # noqa: E402
import _mlr_run       # noqa: E402
import pb_mlr         # noqa: E402

PREREGISTRATION = (Path(__file__).resolve().parents[1] / "evals" / "craft" /
                   "modularity-local-reasoning" / "MLR-paired-q1-preregistration.md")

IDENTITY = "mlr-deepseek-v4-flash-high-paired-q1"
MODEL, VARIANT, REVISION, SAMPLES = "deepseek/deepseek-v4-flash", "high", "q1", 6

# The slot order as the preregistration prints it. Written out rather than regenerated, so that a
# change to the generator fails here instead of quietly redefining what was frozen.
FROZEN_ORDER = [
    (1, "full"), (1, "contract"),
    (2, "contract"), (2, "full"),
    (3, "full"), (3, "contract"),
    (4, "contract"), (4, "full"),
    (5, "full"), (5, "contract"),
    (6, "contract"), (6, "full"),
]

FROZEN_FAMILIES = ("Local source substitution supported", "Representation shifted, not removed",
                   "Implementation access materially useful",
                   "Little meaningful representation difference", "Heterogeneous",
                   "Experiment invalid or stopped")


def configuration():
    return pb_mlr.configuration(model=MODEL, samples=SAMPLES, arms=list(_mlr.ARMS),
                                variant=VARIANT, revision=REVISION)


class FrozenDesignTest(unittest.TestCase):
    """What the preregistration says, and what the machinery does."""

    maxDiff = None

    def test_the_preregistration_is_committed(self):
        self.assertTrue(PREREGISTRATION.is_file())

    def test_the_identity_is_new_and_not_an_r4_continuation(self):
        identity = configuration()["experiment"]
        self.assertEqual(identity, IDENTITY)
        self.assertNotIn("r4", identity)
        self.assertNotEqual(identity, "mlr-deepseek-v4-flash-high-paired-r4")

    def test_the_slot_order_is_exactly_the_frozen_one(self):
        got = [(s["repeat"], s["item"]) for s in pb_mlr.slots(list(_mlr.ARMS), SAMPLES)]
        self.assertEqual(got, FROZEN_ORDER)

    def test_n_is_six_pairs_and_twelve_slots(self):
        self.assertEqual(len(FROZEN_ORDER), 12)
        self.assertEqual(len({pair for pair, _ in FROZEN_ORDER}), SAMPLES)
        for pair in range(1, SAMPLES + 1):
            arms = [arm for p, arm in FROZEN_ORDER if p == pair]
            self.assertEqual(sorted(arms), ["contract", "full"], f"pair {pair}")

    def test_neither_arm_systematically_leads(self):
        """Three pairs each way, so temporal position is never identical to treatment."""
        leads = [arms[0] for arms in (
            [arm for p, arm in FROZEN_ORDER if p == pair] for pair in range(1, SAMPLES + 1))]
        self.assertEqual(leads.count("full"), 3)
        self.assertEqual(leads.count("contract"), 3)

    def test_the_attribution_and_profile_versions_are_the_qualified_ones(self):
        config = configuration()
        self.assertEqual(config["telemetry_version"], "mlr-context-6")
        self.assertEqual(config["profile_version"], "profile-1")

    def test_the_measurand_and_consumed_definition_are_unchanged(self):
        config = configuration()
        self.assertEqual(config["measurand"],
                         "unique bytes of direct implementation-source representation consumed on "
                         "correct runs, per arm")
        self.assertIn("before a later model call", config["consumed_definition"])

    def test_the_retry_cap_is_three(self):
        self.assertEqual(pb_mlr.MAX_ATTEMPTS_PER_SLOT, 3)

    def test_the_frozen_stack_identities_match_the_repository(self):
        config = configuration()
        self.assertEqual(_mlr.digest_tree(_mlr.FIXTURE / "runtime" / "objectstore")[:16],
                         "1f83c3b1f22ab756")
        self.assertEqual(_mlr.digest_file(_mlr.FIXTURE / "tasks" / "external.md")[:16],
                         "eb24429a46ecad4c")
        self.assertEqual(
            _mlr.digest_file(_mlr.FIXTURE / "base" / "docs" / "storage-contract.md")[:16],
            "af3d3e9be15b51ed")
        self.assertEqual(_mlr.digest_file(_mlr.FIXTURE / "hidden" / _mlr_run.ORACLE)[:16],
                         "86f17eaf2685ac22")
        self.assertEqual(config["price_id"], "deepseek-2026-09-09")

    def test_the_hermeticity_rule_covers_what_the_fixture_withholds(self):
        """The rule's identity includes its scan roots, which are host paths.

        So the frozen digest belongs to the execution host, and what is portable is the rule's
        shape: the categories it checks and the fixture digests it checks them by. Asserting the
        digest would be asserting which machine ran the test — the same mistake as asserting which
        Python did.
        """
        rule = _mlr.hermeticity()
        categories = {kind.category for kind in rule["sensitive"]}
        self.assertEqual(len(categories), 5)
        controlled = next(k for k in rule["sensitive"] if k.category == _hermetic.CONTROLLED_EVIDENCE)
        source = sorted((_mlr.FIXTURE / "runtime" / "objectstore").glob("*.py"))
        self.assertEqual(sorted(controlled.digests), sorted(_mlr.digest_file(p) for p in source))
        self.assertEqual(sorted(controlled.stems), sorted(p.name for p in source))
        self.assertTrue(controlled.marks, "the source fingerprint is part of the rule")
        self.assertEqual(rule["declared"], [], "nothing is declared exposed before a run")

    def test_widening_the_rule_changes_its_identity(self):
        """A run that declares an exposure is running a different rule and must say so."""
        base = _mlr.preflight_identity()
        self.assertEqual(base, _mlr.preflight_identity(), "the identity is of the rule")
        widened = _mlr.preflight_identity(declared=[Path("/nowhere/in/particular")])
        self.assertNotEqual(base, widened)

    def test_the_interpreter_is_recorded_from_whatever_launches_the_attempt(self):
        """The frozen stack names CPython 3.9.6 because that is what launches a slot here.

        It is a property of the launcher, not of the fixture, so this checks that the configuration
        reports the running interpreter faithfully and that the preregistration names the one the
        experiment will actually run under. Asserting the literal would only be asserting which
        Python happened to run the test.
        """
        config = configuration()
        self.assertEqual(config["interpreter"]["version"], platform.python_version())
        self.assertIn("CPython 3.9.6", PREREGISTRATION.read_text(encoding="utf-8"))

    def test_the_role_and_permission_flag_are_the_qualified_ones(self):
        self.assertEqual(_mlr_run.ROLE, "implementer")
        self.assertEqual(_mlr_run.AUTO_FLAG, "--auto")


    def test_the_semantic_boundary_binds_its_executor_by_content(self):
        """The property that must hold everywhere: the boundary's identity is of its tools' bytes.

        This used to assert that *this host's* installed `opencode` hashes to `2f24593f1b8e578d`,
        which is not a property of the repository at all — it is a statement about one machine on
        one day, and it failed the moment the host upgraded from 1.18.29 to 1.18.30 while CI, which
        installs no executor at all, silently skipped it. That is the fourth instance of the same
        mistake in this file's history: a host-derived value frozen as though it were portable.

        What is portable is checked here, with a file this test writes: two executors with different
        bytes are two different boundaries, and the same executor is the same boundary every time.
        Whether *this* host may run the frozen experiment is a launch question, not a unit-test
        question, and it is enforced by `_mlr_series.executor_eligibility` — see
        `tests/test_mlr_b1_execution_path.py`, which exercises absent, matching and mismatching
        executors on any platform.
        """
        import _mlr_boundary
        import _mlr_series
        tmp = Path(tempfile.mkdtemp(prefix="pb-q1-exec-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        one, two = tmp / "one", tmp / "two"
        one.write_bytes(b"#!/bin/sh\nexit 0\n")
        two.write_bytes(b"#!/bin/sh\nexit 1\n")

        self.assertEqual(_mlr_boundary.executor_identity(one)["sha256"],
                         _mlr_boundary.executor_identity(one)["sha256"],
                         "an executor's identity is of its bytes, not of the moment")
        self.assertNotEqual(_mlr_boundary.executor_identity(one)["sha256"],
                            _mlr_boundary.executor_identity(two)["sha256"])
        self.assertEqual(_mlr_boundary.policy(executor=one).identity(),
                         _mlr_boundary.policy(executor=one).identity(),
                         "the identity is of the policy, not of the moment")
        self.assertNotEqual(_mlr_boundary.policy(executor=one).identity(),
                            _mlr_boundary.policy(executor=two).identity(),
                            "a different executor is a different boundary")

        # The launch guard still names the qualified executor, so removing the host assertion above
        # has not removed the requirement it was standing in for.
        self.assertEqual(pb_mlr.B1["executor_sha256"], "2f24593f1b8e578d")
        self.assertIn("2f24593f1b8e578d", PREREGISTRATION.read_text(encoding="utf-8"))
        self.assertFalse(
            _mlr_series.executor_eligibility(two, required_sha256="2f24593f1b8e578d")["eligible"])

    def test_the_frozen_boundary_digest_belongs_to_the_host_that_produced_it(self):
        """`b88bd43109184459` is named in the preregistration as a host-derived execution fact.

        Portable on purpose, with no `skipTest`: what it checks is what the *document* says, and
        that is the same on every machine. A version guard here would report "skipped" on every
        host but one, which is the signal that let the executor assertion above stay wrong through
        four corrections.
        """
        text = PREREGISTRATION.read_text(encoding="utf-8")
        self.assertIn("b88bd43109184459", text)
        self.assertIn("CPython 3.9.6", text)
        self.assertIn("interpreter", " ".join(text.split()).lower())

    def test_this_experiment_has_its_own_record_and_cannot_touch_an_older_one(self):
        results = Path(__file__).resolve().parents[1] / "evals" / "results"
        mine = results / f"craft-{IDENTITY}.json"
        r4 = results / "craft-mlr-deepseek-v4-flash-high-paired-r4.json"
        self.assertNotEqual(mine, r4)
        self.assertTrue(r4.is_file(), "the invalid series stays where it is")
        import json
        self.assertEqual(json.loads(r4.read_text())["outcome"]["family"], "Experiment invalid")


class ArmExposureTest(unittest.TestCase):
    """The treatment itself: what each arm can read."""

    maxDiff = None

    def arm(self, name):
        tmp = Path(tempfile.mkdtemp(prefix="pb-q1-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        return _mlr.materialise(name, tmp / "arm")

    def test_full_exposes_the_module_source_and_contract_does_not(self):
        full = self.arm(_mlr.FULL)
        contract = self.arm(_mlr.CONTRACT)
        full_src = Path(full["workspace"]) / _mlr.VENDORED / "objectstore"
        contract_src = Path(contract["workspace"]) / _mlr.VENDORED / "objectstore"
        self.assertTrue(sorted(full_src.glob("*.py")), "full must expose readable source")
        self.assertFalse(contract_src.exists(), "contract must withhold readable source")

    def test_both_arms_share_the_same_compiled_runtime_and_contract(self):
        full = self.arm(_mlr.FULL)
        contract = self.arm(_mlr.CONTRACT)
        self.assertEqual(full["runtime_structure"], contract["runtime_structure"])
        self.assertEqual(full["contract_sha256"], contract["contract_sha256"])
        self.assertEqual(full["source_digest"], contract["source_digest"])

    def test_contract_keeps_an_executable_runtime(self):
        contract = self.arm(_mlr.CONTRACT)
        compiled = sorted((Path(contract["runtime"]) / "objectstore").glob("*.pyc"))
        self.assertTrue(compiled, "contract must keep the executable runtime")

    def test_the_r6_calibration_tasks_are_not_this_experiment_task(self):
        """The calibration stimuli exist, and are not what this experiment runs."""
        tasks = _mlr.FIXTURE / "tasks"
        for name in ("calibration-source-read.md", "calibration-runtime-doc.md"):
            self.assertTrue((tasks / name).is_file())
            self.assertNotEqual(_mlr.digest_file(tasks / name),
                                _mlr.digest_file(tasks / "external.md"))


class ValidityCannotBeLaunderedTest(unittest.TestCase):
    """An attempt that failed must not be able to present itself as a sample."""

    maxDiff = None

    def test_the_validity_states_are_distinct(self):
        states = {_mlr_run.VALID, _mlr_run.SETUP_FAILURE, _mlr_run.HARNESS_FAILURE}
        self.assertEqual(len(states), 3)

    def test_spending_only_counts_priced_attempts(self):
        """A failed attempt with no usage contributes nothing, and cannot inflate the ceiling."""
        self.assertEqual(pb_mlr._spent([{"validity": _mlr_run.SETUP_FAILURE}]), 0.0)
        self.assertEqual(pb_mlr._spent([{"cost": {"amount": 0.01}}]), 0.01)

    def test_every_frozen_result_family_appears_in_the_preregistration(self):
        text = PREREGISTRATION.read_text(encoding="utf-8")
        for family in FROZEN_FAMILIES:
            self.assertIn(family, text, family)

    def test_the_preregistration_states_the_denominator_and_the_scalar_prohibition(self):
        text = PREREGISTRATION.read_text(encoding="utf-8")
        self.assertIn("N = 6 refers to scheduled pairs", text)
        self.assertIn("No scalar.", text)

    def test_the_preregistration_fixes_the_reconstruction_reading(self):
        text = PREREGISTRATION.read_text(encoding="utf-8")
        self.assertIn("not by itself evidence that hidden", text)


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
