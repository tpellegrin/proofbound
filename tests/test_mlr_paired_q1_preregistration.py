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
        self.assertEqual(config["hermeticity_identity"][:16], "dcbf34fb63821980")
        self.assertEqual(config["price_id"], "deepseek-2026-09-09")

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


    def test_the_semantic_boundary_is_the_qualified_one(self):
        """Only checkable where the executor is: the boundary identity binds its tools by digest."""
        executor = shutil.which("opencode")
        if executor is None:                                # pragma: no cover - depends on host
            self.skipTest("the executor is not installed here")
        import _mlr_boundary
        # The executor's bytes are the same whoever asks.
        self.assertEqual(_mlr_boundary.executor_identity(Path(executor))["sha256"][:16],
                         "2f24593f1b8e578d")
        identity = _mlr_boundary.policy(executor=Path(executor)).identity()
        self.assertEqual(identity, _mlr_boundary.policy(executor=Path(executor)).identity(),
                         "the identity is of the policy, not of the moment")
        if not platform.python_version().startswith("3.9."):
            self.skipTest("the boundary exposes the launching interpreter, so the frozen digest "
                          "belongs to CPython 3.9.6")
        self.assertEqual(identity[:16], "b88bd43109184459")

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
