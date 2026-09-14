#!/usr/bin/env python3
"""The frozen design of `mlr-deepseek-v4-flash-high-paired-eventbus-b1`, checked against the machinery.

A cross-fixture replication is only a replication if the fixture is the one thing that moved. These
assert the parts a later edit could silently break: that the identity is new, that fixture B is the
one selected and fixture A is not, that the stack held fixed is the stack q1 used, that the treatment
still exposes and withholds what it claims, and that N, the slot order and the retry cap are the
frozen ones. No provider call is made.
"""
from __future__ import annotations

import hashlib
import platform
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))

import _lineage       # noqa: E402
import _mlr           # noqa: E402
import _mlr_run       # noqa: E402
import pb_mlr         # noqa: E402

PREREGISTRATION = (Path(__file__).resolve().parents[1] / "evals" / "craft" /
                   "modularity-local-reasoning" / "MLR-eventbus-b1-preregistration.md")

IDENTITY = "mlr-deepseek-v4-flash-high-paired-eventbus-b1"
MODEL, VARIANT, REVISION, SAMPLES = "deepseek/deepseek-v4-flash", "high", "eventbus-b1", 6
B = _mlr.EVENTBUS

FROZEN_ORDER = [
    (1, "full"), (1, "contract"),
    (2, "contract"), (2, "full"),
    (3, "full"), (3, "contract"),
    (4, "contract"), (4, "full"),
    (5, "full"), (5, "contract"),
    (6, "contract"), (6, "full"),
]

FROZEN_FAMILIES = ("F · Invalid or stopped", "R3 · No informational pressure",
                   "R2 · Partial replication", "R1 · Core phenomenon replicates",
                   "R4 · Little meaningful difference")


def configuration():
    return pb_mlr.configuration(model=MODEL, samples=SAMPLES, arms=list(_mlr.ARMS),
                                variant=VARIANT, revision=REVISION)


class FrozenDesignTest(unittest.TestCase):
    maxDiff = None

    def test_the_preregistration_is_committed(self):
        self.assertTrue(PREREGISTRATION.is_file())

    def test_the_identity_is_new_and_is_not_q1(self):
        identity = configuration()["experiment"]
        self.assertEqual(identity, IDENTITY)
        self.assertNotEqual(identity, "mlr-deepseek-v4-flash-high-paired-q1")
        self.assertIn("eventbus", identity)

    def test_the_slot_order_is_exactly_the_frozen_one(self):
        got = [(s["repeat"], s["item"]) for s in pb_mlr.slots(list(_mlr.ARMS), SAMPLES)]
        self.assertEqual(got, FROZEN_ORDER)

    def test_n_is_six_pairs_with_neither_arm_leading(self):
        self.assertEqual(len(FROZEN_ORDER), 12)
        leads = [[a for p, a in FROZEN_ORDER if p == pair][0] for pair in range(1, SAMPLES + 1)]
        self.assertEqual(leads.count("full"), 3)
        self.assertEqual(leads.count("contract"), 3)

    def test_the_retry_cap_is_the_q1_cap(self):
        self.assertEqual(pb_mlr.MAX_ATTEMPTS_PER_SLOT, 3)

    def test_the_measurement_system_is_the_one_q1_used(self):
        config = configuration()
        self.assertEqual(config["telemetry_version"], "mlr-context-6")
        self.assertEqual(config["profile_version"], "profile-1")
        self.assertEqual(config["price_id"], "deepseek-2026-09-09")
        self.assertEqual(config["measurand"],
                         "unique bytes of direct implementation-source representation consumed on "
                         "correct runs, per arm")
        self.assertIn("before a later model call", config["consumed_definition"])
        self.assertEqual(_mlr_run.ROLE, "implementer")
        self.assertEqual(_mlr_run.AUTO_FLAG, "--auto")


class FixtureSelectionTest(unittest.TestCase):
    """Fixture B must be the fixture, and fixture A must not be reachable by accident."""

    maxDiff = None

    def test_the_frozen_fixture_digests_match_the_repository(self):
        self.assertEqual(_mlr.digest_tree(B.source)[:16], "9999cc1365c98e23")
        self.assertEqual(_mlr.digest_file(B.root / "tasks" / "external.md")[:16],
                         "d0eb34a91a7b0935")
        self.assertEqual(_mlr.digest_file(B.root / "base" / B.contract)[:16], "0be8e117bbb3050c")
        self.assertEqual(_mlr.digest_file(B.root / "hidden" / "external_test.py")[:16],
                         "542d27df3fff8f52")

    def test_the_replication_does_not_use_the_q1_fixture(self):
        self.assertNotEqual(B.root, _mlr.OBJECTSTORE.root)
        self.assertNotEqual(B.package, _mlr.OBJECTSTORE.package)
        self.assertNotEqual(_mlr.digest_file(B.root / "tasks" / "external.md"),
                            _mlr.digest_file(_mlr.OBJECTSTORE.root / "tasks" / "external.md"))

    def test_no_calibration_task_is_reachable_in_this_fixture(self):
        """The R6 stimuli belong to fixture A and must not be this experiment's task."""
        self.assertEqual(sorted(p.name for p in (B.root / "tasks").glob("*.md")),
                         ["external.md"])

    def test_each_fixture_protects_its_own_module(self):
        self.assertNotEqual(_mlr.preflight_identity(fixture=B.root),
                            _mlr.preflight_identity(fixture=_mlr.OBJECTSTORE.root))


class TreatmentTest(unittest.TestCase):
    maxDiff = None

    def arm(self, name):
        tmp = Path(tempfile.mkdtemp(prefix="pb-b1-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        return _mlr.materialise(name, tmp / "arm", fixture=B.root)

    def test_full_exposes_the_eventbus_source_and_contract_exposes_none(self):
        full, contract = self.arm(_mlr.FULL), self.arm(_mlr.CONTRACT)
        readable = Path(full["workspace"]) / full["vendored"] / full["package"]
        withheld = Path(contract["workspace"]) / contract["vendored"] / contract["package"]
        self.assertTrue(sorted(readable.glob("*.py")))
        self.assertFalse(withheld.exists())

    def test_both_arms_execute_the_same_compiled_runtime(self):
        full, contract = self.arm(_mlr.FULL), self.arm(_mlr.CONTRACT)
        self.assertEqual(full["runtime_structure"], contract["runtime_structure"])
        self.assertEqual(full["contract_sha256"], contract["contract_sha256"])
        for built in (full, contract):
            self.assertTrue(_mlr.executed_module_is_not_the_readable_copy(built)["from_runtime"])

    def test_the_only_arm_difference_is_the_vendored_source(self):
        difference = _mlr.arm_difference(self.arm(_mlr.FULL), self.arm(_mlr.CONTRACT))
        self.assertEqual(difference["only_contract"], [])
        self.assertTrue(difference["only_full"])
        prefix = B.vendored.as_posix() + "/"
        for path in difference["only_full"]:
            self.assertTrue(path.startswith(prefix), path)

    def test_contract_can_read_no_line_of_the_implementation(self):
        contract = self.arm(_mlr.CONTRACT)
        marks = _lineage.source_fingerprint(B.source)
        workspace = Path(contract["workspace"])
        for path in workspace.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            with self.subTest(path=path.relative_to(workspace).as_posix()):
                self.assertEqual(_lineage.source_in(text, marks)["lines"], 0)


class OracleTest(unittest.TestCase):
    """The gate this experiment will be graded by, re-checked at preregistration time."""

    maxDiff = None

    def gate(self, realization=None):
        tmp = Path(tempfile.mkdtemp(prefix="pb-b1-gate-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        built = _mlr.materialise(_mlr.CONTRACT, tmp / "arm", fixture=B.root)
        if realization is not None:
            shutil.copyfile(realization, Path(built["workspace"]) / "app" / "api.py")
        gate = _mlr.run_gate(built, B.root / "hidden" / "external_test.py", data_root=tmp / "g")
        suite = _mlr.run_tests(built, data_root=tmp / "s")
        return gate.returncode == 0, suite.returncode == 0

    def test_the_task_is_not_already_done(self):
        passed, suite = self.gate()
        self.assertFalse(passed)
        self.assertTrue(suite)

    def test_structurally_distinct_correct_solutions_all_pass(self):
        valid = sorted((B.root / "realizations" / "valid").glob("*.py"))
        self.assertGreaterEqual(len(valid), 2)
        for path in valid:
            with self.subTest(realization=path.stem):
                self.assertEqual(self.gate(path), (True, True))

    def test_plausible_wrong_solutions_all_fail(self):
        invalid = sorted((B.root / "realizations" / "invalid").glob("*.py"))
        self.assertGreaterEqual(len(invalid), 3)
        for path in invalid:
            with self.subTest(realization=path.stem):
                self.assertFalse(self.gate(path)[0])


class ExternalityTest(unittest.TestCase):
    """The task must not secretly require changing the module it hides."""

    maxDiff = None

    def test_a_correct_solution_leaves_the_module_untouched(self):
        for realization in sorted((B.root / "realizations" / "valid").glob("*.py")):
            with self.subTest(realization=realization.stem):
                tmp = Path(tempfile.mkdtemp(prefix="pb-b1-ext-"))
                self.addCleanup(shutil.rmtree, tmp, True)
                built = _mlr.materialise(_mlr.FULL, tmp / "arm", fixture=B.root)
                workspace = Path(built["workspace"])
                source = workspace / built["vendored"] / built["package"]
                before, before_runtime = (_mlr.digest_tree(source),
                                          _mlr.digest_tree(Path(built["runtime"])))
                shutil.copyfile(realization, workspace / "app" / "api.py")
                gate = _mlr.run_gate(built, B.root / "hidden" / "external_test.py",
                                     data_root=tmp / "g")
                self.assertEqual(gate.returncode, 0)
                self.assertEqual(_mlr.digest_tree(source), before)
                self.assertEqual(_mlr.digest_tree(Path(built["runtime"])), before_runtime)

    def test_the_contract_states_what_the_caller_needs_and_nothing_private(self):
        import _mlr_context
        contract = (B.root / "base" / B.contract).read_text(encoding="utf-8")
        for needed in ("does not prevent the others", "never propagated to the caller",
                       "receipt.failures", "exactly once per `publish`"):
            self.assertIn(needed, contract)
        marks = _lineage.source_fingerprint(B.source)
        self.assertEqual(_lineage.source_in(contract, marks)["lines"], 0)
        private = set(_mlr_context.internal_names(B.source))
        self.assertTrue(private, "the module must have private names worth hiding")
        self.assertEqual([n for n in sorted(private) if n in contract], [])


class PreregistrationContentTest(unittest.TestCase):
    """The document must actually say the things the design depends on."""

    maxDiff = 400

    def setUp(self):
        self.raw = PREREGISTRATION.read_text(encoding="utf-8")
        # The document is hard-wrapped, so a phrase may straddle a line break. Searching the
        # wrapped text would be asserting where the lines happened to end.
        self.text = " ".join(self.raw.split())

    def test_every_result_family_is_present(self):
        for family in FROZEN_FAMILIES:
            with self.subTest(family=family):
                self.assertTrue(family in self.text, f"missing result family: {family}")

    def test_the_denominator_and_the_scalar_prohibition_are_stated(self):
        self.assertTrue("N = 6 refers to scheduled pairs" in self.text, "N = 6 refers to scheduled pairs")
        self.assertTrue("No scalar" in self.text, "No scalar")

    def test_the_n_contamination_barrier_is_stated(self):
        self.assertTrue("No value q1 observed may justify N" in self.text, "No value q1 observed may justify N")

    def test_replication_is_not_defined_as_matching_numbers(self):
        self.assertTrue("Numerical equality is not required" in self.text, "Numerical equality is not required")

    def test_the_cross_fixture_comparison_is_deferred_until_after(self):
        self.assertIn("only after", self.text.lower())

    def test_the_host_derived_identity_policy_is_carried_forward(self):
        self.assertTrue("recorded per slot as execution facts" in self.text, "recorded per slot as execution facts")

    def test_the_interpreter_dependent_runtime_digest_is_not_frozen_as_a_constant(self):
        """The fixture-B compiled structure belongs to whichever interpreter compiled it."""
        tmp = Path(tempfile.mkdtemp(prefix="pb-b1-rt-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        built = _mlr.materialise(_mlr.FULL, tmp / "arm", fixture=B.root)
        if platform.python_version().startswith("3.9."):
            self.assertEqual(built["runtime_structure"][:16], "31b1a993a165e75c")
        self.assertNotIn(built["runtime_structure"], self.raw,
                         "a compiled digest must not be frozen as though it were portable")


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()
